from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from PIL import Image, ImageDraw, ImageFont
import io, sys
f = TTFont('src/fonts/bodoni-moda-latin-opsz-italic.woff2')
f.flavor = None
axes = {a.axisTag: a for a in f['fvar'].axes}
loc = {}
if 'opsz' in axes: loc['opsz'] = axes['opsz'].maxValue
if 'wght' in axes: loc['wght'] = 500
f = instancer.instantiateVariableFont(f, loc)
buf = io.BytesIO(); f.save(buf); buf.seek(0)
COL = ['#A3305F', '#0A6A86', '#87283A', '#2D4A8C']
def icon(size, pad_frac=0.0):
    S = 1024
    im = Image.new('RGB', (S, S), COL[3])
    d = ImageDraw.Draw(im)
    h = S // 2
    d.rectangle([0, 0, h, h], fill=COL[0]); d.rectangle([h, 0, S, h], fill=COL[1])
    d.rectangle([0, h, h, S], fill=COL[2]); d.rectangle([h, h, S, S], fill=COL[3])
    buf.seek(0)
    font = ImageFont.truetype(buf, int(S * (0.74 - pad_frac)))
    bb = d.textbbox((0, 0), 'E', font=font)
    w, hh = bb[2] - bb[0], bb[3] - bb[1]
    d.text(((S - w) / 2 - bb[0] + S * 0.01, (S - hh) / 2 - bb[1]), 'E', font=font, fill='#FFFFFF')
    return im.resize((size, size), Image.LANCZOS)
icon(180).save('src/icons/apple-touch-icon.png')
icon(192).save('src/icons/icon-192.png')
icon(512).save('src/icons/icon-512.png')
icon(512, 0.2).save('src/icons/icon-maskable-512.png')
print('icons ok')
