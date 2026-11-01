"""Prototype: render a markdown table to a PNG by MEASURING glyphs from the real font files.

Nothing here counts characters. Every run of text is measured with the font that draws it,
columns are sized in pixels, cells are wrapped by pixel width and every wrapped line is
aligned from its own measured width. A self-check reads the finished picture back.
"""
import json
import os
import sys
import unicodedata

from PIL import Image, ImageDraw, ImageFont

WIN = r"C:\Windows\Fonts"
FONT_FILES = {
    "main": (os.path.join(WIN, "consola.ttf"), 0),
    "main_b": (os.path.join(WIN, "consolab.ttf"), 0),
    "main_i": (os.path.join(WIN, "consolai.ttf"), 0),
    "main_bi": (os.path.join(WIN, "consolaz.ttf"), 0),
    "cjk": (os.path.join(WIN, "msyh.ttc"), 0),
    "cjk_b": (os.path.join(WIN, "msyhbd.ttc"), 0),
    "emoji": (os.path.join(WIN, "seguiemj.ttf"), 0),
    "ui": (os.path.join(WIN, "segoeui.ttf"), 0),
    "ui_b": (os.path.join(WIN, "segoeuib.ttf"), 0),
    "sym": (os.path.join(WIN, "seguisym.ttf"), 0),
    "hangul": (os.path.join(WIN, "malgun.ttf"), 0),
    "hangul_b": (os.path.join(WIN, "malgunbd.ttf"), 0),
}

# Scripts and sequences that need a text-shaping engine (contextual forms, bidi, combining
# clusters). Pillow here has no raqm, so they cannot be drawn faithfully: the renderer REFUSES
# the table (ShapingNeeded) and the caller keeps its own layout.
NEEDS_SHAPING = (
    (0x0590, 0x08FF), (0x0900, 0x0DFF), (0x0E00, 0x0EFF), (0x0F00, 0x109F), (0x1780, 0x17FF),
    (0xFB1D, 0xFDFF), (0xFE70, 0xFEFF), (0x200D, 0x200D), (0x1F1E6, 0x1F1FF), (0x1F3FB, 0x1F3FF),
)


class ShapingNeeded(Exception):
    pass


def needs_shaping(ch):
    cp = ord(ch)
    if unicodedata.combining(ch):  # a mark that NFC could not fold into its letter
        return True
    return any(a <= cp <= b for a, b in NEEDS_SHAPING)

# Colours sampled from the real preview screenshot (see sample_colours.py output).
THEME = {
    "surface": (61, 69, 78, 255),
    "border": (88, 96, 105, 255),
    "fg": (216, 222, 233, 255),
    "muted_rule": (88, 96, 105, 255),
}


_COVER = {}


def _has_glyph(key, ch):
    """True if the font file `key` draws a real glyph for ch (its .notdef box does not count)."""
    k = (key, ch)
    if k not in _COVER:
        if key not in _COVER_FONTS:
            path, idx = FONT_FILES[key]
            _COVER_FONTS[key] = ImageFont.truetype(path, 32, index=idx)
        face = _COVER_FONTS[key]
        try:
            m, nd = face.getmask(ch), face.getmask("\U0010ffff")
            _COVER[k] = not (m.size == nd.size and bytes(m) == bytes(nd))
        except Exception:
            _COVER[k] = False
    return _COVER[k]


_COVER_FONTS = {}


def kind_of(ch):
    """Which font draws ch: the first in the chain that really has a glyph for it ('none' = no font)."""
    cp = ord(ch)
    if cp < 0x80 or ch.isspace():
        return "main"
    if 0x1F000 <= cp < 0x20000 or cp in (0x2B50, 0x2B55, 0x231A, 0x231B) or cp in EMOJI_PRESENT:
        return "emoji"
    wide = unicodedata.east_asian_width(ch) in ("W", "F")
    chain = ("cjk", "hangul", "main", "ui", "sym", "emoji") if wide else ("main", "ui", "sym", "cjk", "hangul", "emoji")
    for key in chain:
        probe = {"cjk": "cjk", "hangul": "hangul", "main": "main", "ui": "ui", "sym": "sym", "emoji": "emoji"}[key]
        if _has_glyph(probe, ch):
            return key
    return "none"


# Dingbat/misc-symbol code points that default to emoji presentation; the rest (check marks,
# stars, hearts) are drawn by the symbol font so they look like text, as the text layout does.
EMOJI_PRESENT = set(range(0x2614, 0x2616)) | {0x2648 + i for i in range(12)} | {0x267F, 0x2693, 0x26A1, 0x26AA, 0x26AB, 0x26BD, 0x26BE, 0x26C4, 0x26C5, 0x26CE, 0x26D4, 0x26EA, 0x26F2, 0x26F3, 0x26F5, 0x26FA, 0x26FD, 0x2705, 0x270A, 0x270B, 0x2728, 0x274C, 0x274E, 0x2753, 0x2754, 0x2755, 0x2757, 0x2795, 0x2796, 0x2797, 0x27B0, 0x27BF}


class Fonts:
    def __init__(self, size, scale):
        self.px = size * scale
        self.f = {}
        for key, (path, idx) in FONT_FILES.items():
            self.f[key] = ImageFont.truetype(path, self.px, index=idx)
        self.asc, self.desc = self.f["main"].getmetrics()

    def face(self, kind, bold, ital=False):
        if kind == "emoji":
            return self.f["emoji"]
        if kind in ("cjk", "hangul", "ui"):  # no italic file used for these: upright
            return self.f[kind + ("_b" if bold else "")]
        if kind == "sym":
            return self.f["sym"]
        return self.f["main" + ("_" if (bold or ital) else "") + ("b" if bold else "") + ("i" if ital else "")]

    def names(self):
        return {k: v.getname() for k, v in self.f.items()}

    def runs(self, text, base_bold, st=(False, False)):
        """[(kind, text, bold, italic)]; style markers are zero width and switch bold/italic."""
        out = []
        sb, si = st
        for ch in text:
            if ch in MARKS:
                sb, si = apply_mark(ch, sb, si)
                continue
            k = kind_of(ch)
            b = base_bold or sb
            if out and out[-1][0] == k and out[-1][2] == b and out[-1][3] == si:
                out[-1][1] += ch
            else:
                out.append([k, ch, b, si])
        return [tuple(r) for r in out]

    def width(self, text, base_bold, st=(False, False)):
        return sum(self.face(k, b, i).getlength(s) for k, s, b, i in self.runs(text, base_bold, st))


B1, B0, I1, I0 = "", "", "", ""  # bold on/off, italic on/off (cell markup)
MARKS = (B1, B0, I1, I0)


def apply_mark(ch, sb, si):
    if ch == B1:
        return True, si
    if ch == B0:
        return False, si
    if ch == I1:
        return sb, True
    return sb, False


def state_after(text, st):
    sb, si = st
    for ch in text:
        if ch in MARKS:
            sb, si = apply_mark(ch, sb, si)
    return sb, si


def plain(text):
    return "".join(ch for ch in text if ch not in MARKS)


def min_atom(fonts, text, base):
    st, m = (False, False), 0.0
    for w in atoms(text):
        for a in w:
            m = max(m, fonts.width(a, base, st))
            st = state_after(a, st)
    return m


def atoms(text):
    """Words, with every CJK glyph its own atom (it may start a line). Returns [[atom,...], ...] per word."""
    words = []
    def flush(cur, buf):
        # a word longer than 12 characters may break anywhere (like CSS overflow-wrap:anywhere):
        # chunks of 3 keep lines packed; style markers stay attached to their chunk
        if sum(1 for c in buf if c not in MARKS) > 12:
            chunk, n = "", 0
            for c in buf:
                chunk += c
                if c not in MARKS:
                    n += 1
                if n == 3:
                    cur.append(chunk)
                    chunk, n = "", 0
            if chunk:
                cur.append(chunk)
        else:
            cur.append(buf)

    words = []
    for w in text.split():
        cur, buf = [], ""
        for ch in w:
            if kind_of(ch) == "cjk":
                if buf:
                    flush(cur, buf)
                    buf = ""
                cur.append(ch)
            else:
                buf += ch
        if buf:
            flush(cur, buf)
        words.append(cur)
    return words


def wrap(fonts, text, bold, width):
    space = fonts.width(" ", bold)
    st = (False, False)
    lines, line, lw, has = [], "", 0.0, False
    for word in atoms(text):
        for i, a in enumerate(word):
            aw = fonts.width(a, bold, st)
            glue = space if (i == 0 and has) else 0.0
            if has and lw + glue + aw > width + 0.01:
                lines.append((line, lw))
                # a new line re-opens whatever style is still active
                line, lw, glue, has = (B1 if st[0] else "") + (I1 if st[1] else ""), 0.0, 0.0, False
            line += (" " if glue else "") + a
            lw += glue + aw
            has = True
            st = state_after(a, st)
    lines.append((line, lw))
    return lines


def layout_columns(fonts, header, rows, avail, gap):
    n = len(header)
    cells = [header] + rows
    nat, mn = [0.0] * n, [0.0] * n
    for ri, row in enumerate(cells):
        bold = ri == 0
        for c, text in enumerate(row):
            nat[c] = max(nat[c], fonts.width(text, bold) if text else 0.0)
            ms = min_atom(fonts, text, bold)
            mn[c] = max(mn[c], ms)
    room = avail - gap * (n - 1)
    if sum(nat) <= room:
        return nat, False
    if sum(mn) >= room:
        return mn, True
    # Water-filling: a column never goes below its widest unbreakable atom, and only the
    # columns wider than the common level are squeezed; short columns keep their natural width.
    lo, hi = 0.0, max(nat)
    for _ in range(50):
        level = (lo + hi) / 2
        if sum(min(a, max(m, level)) for m, a in zip(mn, nat)) > room:
            hi = level
        else:
            lo = level
    return [min(a, max(m, lo)) for m, a in zip(mn, nat)], False


def render(header, rows, aligns, pane_width, scale=1, size=16, out_path=None):
    fonts = Fonts(size, scale)
    S = scale
    header = [unicodedata.normalize("NFC", t) for t in header]
    rows = [[unicodedata.normalize("NFC", t) for t in r] for r in rows]
    refused = sorted({ch for row in [header] + rows for t in row for ch in plain(t) if needs_shaping(ch) or kind_of(ch) == "none"})
    if refused:
        raise ShapingNeeded("cannot draw faithfully: " + " ".join("U+%04X" % ord(c) for c in refused[:12]))
    pad_x, pad_y, border, gap = round(16 * S), round(13.6 * S), max(1, round(1.3 * S)), round(20 * S)
    lh = round(23.2 * S)
    rule_gap = round(5 * S)
    avail = pane_width * S - 2 * (pad_x + border)
    widths, overflow = layout_columns(fonts, header, rows, avail - len(header), gap)  # 1 px per column for rounding up
    widths = [int(w + 0.999) for w in widths]  # whole pixels
    inner_w = sum(widths) + gap * (len(widths) - 1)
    total_w = inner_w + 2 * (pad_x + border)

    # wrap every cell
    wrapped = []
    for ri, row in enumerate([header] + rows):
        bold = ri == 0
        wrapped.append([wrap(fonts, t, bold, widths[c]) for c, t in enumerate(row)])
    heights = [max(len(c) for c in r) * lh for r in wrapped]
    total_h = 2 * (pad_y + border) + sum(heights) + rule_gap * 2 + border
    img = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([0, 0, total_w - 1, total_h - 1], radius=round(5.6 * S), fill=THEME["surface"], outline=THEME["border"], width=border)

    col_x = []
    x = pad_x + border
    for w in widths:
        col_x.append(x)
        x += w + gap
    placed = []  # for the self-check
    y = pad_y + border
    for ri, row in enumerate(wrapped):
        bold = ri == 0
        for c, lines in enumerate(row):
            for li, (text, lw) in enumerate(lines):
                if aligns[c] == "r":
                    lx = col_x[c] + widths[c] - lw
                elif aligns[c] == "c":
                    lx = col_x[c] + (widths[c] - lw) / 2
                else:
                    lx = col_x[c]
                lx = round(lx)
                base = y + li * lh + (lh - (fonts.asc + fonts.desc)) // 2 + fonts.asc
                cx = lx
                for k, s, rb, ri_ in fonts.runs(text, bold):
                    face = fonts.face(k, rb, ri_)
                    if k == "emoji":
                        d.text((cx, base), s, font=face, embedded_color=True, anchor="ls")
                    else:
                        d.text((cx, base), s, font=face, fill=THEME["fg"], anchor="ls")
                    cx += face.getlength(s)
                placed.append(dict(row=ri, col=c, line=li, text=plain(text), x=lx, w=lw, top=y + li * lh, col_x=col_x[c], col_w=widths[c], align=aligns[c]))
        y += heights[ri]
        if ri == 0:
            y += rule_gap
            d.line([(pad_x + border, y - 1), (total_w - pad_x - border - 1, y - 1)], fill=THEME["muted_rule"], width=border)
            y += rule_gap
    if out_path:
        img.save(out_path)
    return img, placed, dict(width=total_w, height=total_h, overflow=overflow, widths=widths, names=fonts.names(), lh=lh, scale=S)


def ink_bbox(img, box):
    """Bounding box of pixels that differ from the surface inside `box`, or None."""
    x0, y0, x1, y1 = box
    px = img.load()
    sx, sy = THEME["surface"][:3], None
    minx = miny = 10 ** 9
    maxx = maxy = -1
    for yy in range(max(0, y0), min(img.height, y1)):
        for xx in range(max(0, x0), min(img.width, x1)):
            p = px[xx, yy]
            if abs(p[0] - sx[0]) + abs(p[1] - sx[1]) + abs(p[2] - sx[2]) > 90 and p[3] > 0:
                minx, maxx = min(minx, xx), max(maxx, xx)
                miny, maxy = min(miny, yy), max(maxy, yy)
    return None if maxx < 0 else (minx, miny, maxx + 1, maxy + 1)


def self_check(img, placed, info, expect_cells):
    problems, worst = [], {"l": 0.0, "r": 0.0, "c": 0.0}
    lh = info["lh"]
    by_col_header = {}
    for p in placed:
        box = (p["col_x"] - 3, p["top"], p["col_x"] + p["col_w"] + 3, p["top"] + lh)
        bb = ink_bbox(img, box)
        if p["text"].strip() and bb is None:
            problems.append("no ink for %r" % p["text"])
            continue
        if bb is None:
            continue
        if p["align"] == "l":
            dev = abs(bb[0] - p["col_x"])
        elif p["align"] == "r":
            dev = abs(bb[2] - (p["col_x"] + p["col_w"]))
        else:
            dev = abs((bb[0] + bb[2]) / 2 - (p["col_x"] + p["col_w"] / 2))
        worst[p["align"]] = max(worst[p["align"]], dev)
        if p["row"] == 0 and p["align"] == "c":
            by_col_header.setdefault(p["col"], []).append((bb[0] + bb[2]) / 2)
    spread = {c: round(max(v) - min(v), 2) for c, v in by_col_header.items()}
    present = {(p["row"], p["col"]) for p in placed if p["text"].strip()}
    for r, c, t in expect_cells:
        if (r, c) not in present:
            problems.append("missing cell row %d col %d %r" % (r, c, t))
    return dict(worst_ink_dev_px=worst, header_centre_spread_px=spread, problems=problems)


def sample_checks():
    return None


TABLES = {
    "A_emoji_xx_control": (["h1", "emoji xx", "very " * 19 + "very long header", "x"]),
    "B_emoji_wide": (["h1", "emoji \U0001F600", "very " * 19 + "very long header", "x"]),
    "C_abcdef_control": (["abcdef", "h2", "very " * 19 + "very long header", "x"]),
    "D_cjk_wide": (["\u65e5\u672c\u8a9e", "h2", "very " * 19 + "very long header", "x"]),
}
ALIGNS = ["l", "r", "c", "l"]
ROW = ["a", "b", "c", "d"]

if __name__ == "__main__":
    outdir = sys.argv[1]
    widths = [int(w) for w in sys.argv[2:]] or [788]
    os.makedirs(outdir, exist_ok=True)
    report = {}
    for pane in widths:
        for name, header in TABLES.items():
            path = os.path.join(outdir, "t%d_%s.png" % (pane, name))
            img, placed, info = render(header, [ROW], ALIGNS, pane, 1, 16, path)
            expect = [(1, c, t) for c, t in enumerate(ROW)]
            res = self_check(img, placed, info, expect)
            report["%d/%s" % (pane, name)] = dict(size=(info["width"], info["height"]), overflow=info["overflow"], widths=info["widths"], **res)
    report["fonts"] = Fonts(16, 1).names()
    with open(os.path.join(outdir, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)
    for k, v in report.items():
        if k == "fonts":
            continue
        print(k, v["size"], "widths", v["widths"], "ink-dev", v["worst_ink_dev_px"], "hdr-centre-spread", v["header_centre_spread_px"], "problems", v["problems"])
