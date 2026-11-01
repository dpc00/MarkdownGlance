import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stress_test as S  # noqa: E402
import table_render as T  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

pane = int(sys.argv[1])
names = sys.argv[3:]
out = sys.argv[2]
tiles = []
for n in names:
    header, rows, al = S.CASES[n]
    aligns = [{"l": "l", "r": "r", "c": "c"}[a] for a in (list(al) + ["l"] * len(header))[: len(header)]]
    try:
        img = T.render(header, rows, aligns, pane, 1, 16, None)[0]
    except T.ShapingNeeded as exc:
        img = Image.new("RGBA", (pane, 24), (90, 30, 30, 255))
        ImageDraw.Draw(img).text((4, 4), "REFUSED " + str(exc)[:80], fill=(255, 255, 255, 255))
    tiles.append((n, img))
W = max(i.width for _, i in tiles) + 20
H = sum(i.height + 26 for _, i in tiles) + 10
sheet = Image.new("RGBA", (W, H), (30, 33, 38, 255))
d = ImageDraw.Draw(sheet)
y = 6
for n, i in tiles:
    d.text((10, y), "%s @%d  (%dx%d)" % (n, pane, i.width, i.height), fill=(200, 200, 120, 255))
    sheet.paste(i, (10, y + 16), i)
    y += i.height + 26
sheet.convert("RGB").save(out)
print(sheet.size)
