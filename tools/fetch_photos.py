"""Downloads one photo per idea from Wikipedia, shrinks it to WebP and records
map coordinates. Runs on GitHub Actions (which has normal internet access).

Only fetches what is missing, so re-running is cheap. Results:
  photos/<item-id>.webp
  photos/manifest.json  {"done": {id: url-or-""}, "geo": {title: [lat, lon]}}
"""
import concurrent.futures as cf
import io, json, os, sys, time, urllib.parse, urllib.request

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "photos")
API = "https://en.wikipedia.org/w/api.php"
REPO = os.environ.get("GITHUB_REPOSITORY", "personal/europe-trips")
UA = f"EuropeFourSeasonsTripGuide/1.0 (https://github.com/{REPO}; personal trip planner)"
MAX_W, MAX_H, QUALITY = 720, 640, 62


def get(url, binary=False, tries=6):
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
                return data if binary else json.loads(data)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                wait = float(e.headers.get("Retry-After") or 0) or min(60, 2 ** n * 2)
                time.sleep(wait)
                continue
            if e.code == 404:
                return None
            raise
        except Exception:
            time.sleep(min(30, 2 ** n))
    return None


def api(params):
    q = dict(action="query", format="json", formatversion="2", **params)
    return get(API + "?" + urllib.parse.urlencode(q)) or {}


def lookup_titles(titles):
    """title -> (thumb url or '', [lat, lon] or None)"""
    res = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        j = api(dict(titles="|".join(batch), redirects="1", prop="pageimages|coordinates",
                     piprop="thumbnail", pithumbsize="960", pilicense="any", colimit="max"))
        qy = j.get("query", {})
        norm = {x["from"]: x["to"] for x in qy.get("normalized", [])}
        red = {x["from"]: x["to"] for x in qy.get("redirects", [])}
        pages = {p["title"]: p for p in qy.get("pages", [])}
        for t in batch:
            k = norm.get(t, t)
            k = red.get(k, k)
            p = pages.get(k, {})
            thumb = (p.get("thumbnail") or {}).get("source", "")
            co = p.get("coordinates")
            geo = [round(co[0]["lat"], 4), round(co[0]["lon"], 4)] if co else None
            res[t] = (thumb, geo)
        time.sleep(0.3)
        print(f"  looked up {min(i + 50, len(titles))}/{len(titles)} titles", flush=True)
    return res


def search_image(query):
    j = api(dict(generator="search", gsrsearch=query, gsrlimit="3", gsrnamespace="0",
                 prop="pageimages", piprop="thumbnail", pithumbsize="960", pilicense="any"))
    pages = sorted(j.get("query", {}).get("pages", []), key=lambda p: p.get("index", 0))
    for p in pages:
        if p.get("thumbnail"):
            return p["thumbnail"]["source"]
    return ""


def save_webp(item_id, url):
    data = get(url, binary=True)
    if not data:
        return False
    try:
        im = Image.open(io.BytesIO(data))
        im.seek(0)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
        im.thumbnail((MAX_W, MAX_H), Image.LANCZOS)
        im.save(os.path.join(OUT, item_id + ".webp"), "WEBP", quality=QUALITY, method=5)
        return True
    except Exception as e:
        print("  bad image", item_id, e)
        return False


def main():
    os.makedirs(OUT, exist_ok=True)
    data = json.load(open(os.path.join(ROOT, "src", "data.json"), encoding="utf-8"))
    mpath = os.path.join(OUT, "manifest.json")
    man = json.load(open(mpath, encoding="utf-8")) if os.path.exists(mpath) else {"done": {}, "geo": {}}
    items = [(c, it) for c in data["countries"] for it in c["items"]]
    retry_none = "--retry-none" in sys.argv

    def needed(it):
        if os.path.exists(os.path.join(OUT, it["id"] + ".webp")):
            return False
        return it["id"] not in man["done"] or (retry_none and man["done"][it["id"]] == "")

    todo = [(c, it) for c, it in items if needed(it)]
    titles = sorted({it["k"] for c, it in items if it["k"] not in man["geo"] or needed(it)})
    print(f"{len(items)} ideas, {len(todo)} photos to fetch, {len(titles)} titles to look up", flush=True)
    found = lookup_titles(titles) if titles else {}
    for t, (thumb, geo) in found.items():
        if geo:
            man["geo"][t] = geo

    urls = {}
    for n, (c, it) in enumerate(todo):
        thumb = found.get(it["k"], ("", None))[0]
        if not thumb:
            thumb = search_image(f'{it["n"]} {c["name"]}')
            time.sleep(0.2)
        urls[it["id"]] = thumb
        if n % 200 == 0:
            print(f"  resolved {n}/{len(todo)}", flush=True)

    ok = 0
    with cf.ThreadPoolExecutor(4) as ex:
        futs = {ex.submit(save_webp, i, u): i for i, u in urls.items() if u}
        for n, f in enumerate(cf.as_completed(futs)):
            i = futs[f]
            if f.result():
                ok += 1
                man["done"][i] = urls[i]
            if n % 100 == 0:
                print(f"  downloaded {n}/{len(futs)}", flush=True)
                json.dump(man, open(mpath, "w", encoding="utf-8"), ensure_ascii=False)
    for i, u in urls.items():
        if not u:
            man["done"][i] = ""
    json.dump(man, open(mpath, "w", encoding="utf-8"), ensure_ascii=False)
    have = len([f for f in os.listdir(OUT) if f.endswith(".webp")])
    size = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT) if f.endswith(".webp"))
    print(f"downloaded {ok} new; {have}/{len(items)} ideas have photos ({size / 1e6:.0f} MB); "
          f"{sum(1 for v in man['done'].values() if v == '')} have none on Wikipedia")


if __name__ == "__main__":
    main()
