"""Builds the offline web app into site/ from src/ and photos/.

site/index.html is self-contained (data, map outline, fonts and Leaflet inline);
photos live in site/photos/ and are cached by the service worker.
"""
import base64, hashlib, json, math, os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
PHOTOS = os.environ.get("PHOTOS_DIR") or os.path.join(ROOT, "photos")
OUT = os.environ.get("SITE_DIR") or os.path.join(ROOT, "site")

LATIN = "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD"
LATIN_EXT = "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF"
FONTS = [
    ("Bodoni Moda", "bodoni-moda-{sub}-opsz-{style}.woff2"),
    ("Schibsted Grotesk", "schibsted-grotesk-{sub}-wght-{style}.woff2"),
]


def read(p, mode="r"):
    with open(os.path.join(SRC, p), mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        return f.read()


def font_css():
    css = []
    for fam, pat in FONTS:
        for style in ("normal", "italic"):
            for sub, rng in (("latin-ext", LATIN_EXT), ("latin", LATIN)):
                data = base64.b64encode(read("fonts/" + pat.format(sub=sub, style=style), "rb")).decode()
                css.append(f"@font-face{{font-family:'{fam}';font-style:{style};font-display:swap;font-weight:400 900;"
                           f"src:url(data:font/woff2;base64,{data}) format('woff2');unicode-range:{rng}}}")
    return "\n".join(css)


def km(a, b):
    r = math.pi / 180
    dlat, dlon = (b[0] - a[0]) * r, (b[1] - a[1]) * r
    h = math.sin(dlat / 2) ** 2 + math.cos(a[0] * r) * math.cos(b[0] * r) * math.sin(dlon / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def build():
    data = json.loads(read("data.json"))
    manifest = {}
    mpath = os.path.join(PHOTOS, "manifest.json")
    if os.path.exists(mpath):
        manifest = json.load(open(mpath, encoding="utf-8"))
    geo = manifest.get("geo", {})
    have = {}
    total_bytes = 0
    if os.path.isdir(PHOTOS):
        for fn in os.listdir(PHOTOS):
            if fn.endswith(".webp"):
                have[fn[:-5]] = os.path.getsize(os.path.join(PHOTOS, fn))

    photos, refined = {}, 0
    for c in data["countries"]:
        for it in c["items"]:
            if it["id"] in have:
                photos[it["id"]] = 1
                total_bytes += have[it["id"]]
            w = geo.get(it["k"])
            if w:
                ref = it.get("g") or c.get("at")
                if ref and km(w, ref) < (350 if it.get("g") else 900):
                    it["g"] = w
                    refined += 1

    version = hashlib.sha1((json.dumps(data, sort_keys=True) + read("app.html") + str(sorted(photos))).encode()).hexdigest()[:10]
    html = read("app.html")
    js_data = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    basemap = read("basemap.json").replace("</", "<\\/")
    rep = {
        "/*__FONTS__*/": font_css(),
        "/*__LEAFLET_CSS__*/": read("leaflet.css"),
        "/*__LEAFLET_JS__*/": read("leaflet.js").replace("</script", "<\\/script"),
        "/*__FIREBASE_JS__*/": read("firebase.bundle.js").replace("</script", "<\\/script"),
        "__PHOTOS_MB__": str(max(1, round(total_bytes / 1e6))),
        "__VERSION__": version,
    }
    for a, b in rep.items():
        html = html.replace(a, b)
    cfg_path = os.path.join(SRC, "firebase-config.json")
    fbcfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) and not os.environ.get("NO_SYNC") else None
    html = html.replace("__FIREBASE_CONFIG__", json.dumps(fbcfg))
    html = html.replace("__PHOTOS__", json.dumps(photos, separators=(",", ":")))
    html = html.replace("__BASEMAP__", basemap)
    html = html.replace("__DATA__", js_data)

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "icons"))
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    for fn in os.listdir(os.path.join(SRC, "icons")):
        shutil.copy(os.path.join(SRC, "icons", fn), os.path.join(OUT, "icons", fn))
    sw = read("sw.js").replace("__VERSION__", version)
    with open(os.path.join(OUT, "sw.js"), "w", encoding="utf-8") as f:
        f.write(sw)
    shutil.copy(os.path.join(SRC, "manifest.webmanifest"), os.path.join(OUT, "manifest.webmanifest"))
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    if photos:
        os.makedirs(os.path.join(OUT, "photos"))
        for pid in photos:
            shutil.copy(os.path.join(PHOTOS, pid + ".webp"), os.path.join(OUT, "photos", pid + ".webp"))

    n = sum(len(c["items"]) for c in data["countries"])
    print(f"site/index.html {len(html) // 1024} KB, {n} items, {len(photos)} photos ({total_bytes / 1e6:.0f} MB), "
          f"{refined} pins refined, version {version}")


if __name__ == "__main__":
    build()
