"""Stress test for table_render: many odd tables x several pane widths, invariants checked from the PICTURE."""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import table_render as T  # noqa: E402
from PIL import features  # noqa: E402

B1, B0, I1, I0 = T.B1, T.B0, T.I1, T.I0
LONGW = "very " * 19 + "very long header"
URL = "https://example.com/a/really/long/path/that/never/breaks/at/all/anywhere/ok?x=1&y=2"
CASES = {
    "basic": (["Item", "Qty", "Notes"], [["Apples", "12", "fresh"], ["Pears", "3", "ok"]], "lrc"),
    "empty_cells": (["a", "b", "c"], [["", "x", ""], ["", "", ""], ["y", "", "z"]], "lcr"),
    "empty_header": (["", "b", ""], [["1", "2", "3"]], "lcr"),
    "header_only": (["a", "b"], [], "lr"),
    "single_col": (["Only"], [["one"], ["two two two"], [LONGW]], "l"),
    "twelve_cols": ([f"c{i}" for i in range(12)], [[str(i * 111) for i in range(12)]] * 3, "lrcl" * 3),
    "long_url": (["Link", "Note"], [[URL, "x"], ["short", URL]], "lr"),
    "long_cjk": (["k", "text"], [["1", "日本語の長い文章がここにあります。これはセルの中で折り返されなければなりません。" * 2]], "lc"),
    "fullwidth_punct": (["a", "b"], [["「こんにちは」、世界！（テスト）", "ＡＢＣ１２３"]], "lr"),
    "emoji_mix": (["e", "t"], [["😀😃😄 text 🍎🍌", "👍 ok"], ["⭐ star ❤ heart ✔ check", "🚀"]], "lc"),
    "emoji_zwj_flags": (["e"], [["👨‍👩‍👧 family"], ["🇯🇵 flag"], ["👍🏽 skin tone"], ["❤️ vs16"]], "l"),
    "combining": (["e"], [["é ä ñ (combining)"], ["Ünïcödé ñ ç ß"]], "l"),
    "greek_cyrillic": (["g", "c"], [["αβγδ Ελληνικά", "Привет мир"]], "lr"),
    "arabic": (["a"], [["مرحبا بالعالم"]], "l"),
    "hebrew": (["h"], [["שלום עולם"]], "l"),
    "thai": (["t"], [["สวัสดีชาวโลก"]], "l"),
    "devanagari": (["d"], [["नमस्ते दुनिया"]], "l"),
    "korean": (["k"], [["안녕하세요 세계"]], "l"),
    "symbols": (["s"], [["→ ← ↑ ↓ ≤ ≥ ≠ ∑ √ ∞ © ® ™ € £ ¥"], ["█ ░ ▒ ┌─┐ │ └─┘ ✓ ✗ ★ ☆"]], "l"),
    "numbers_right": (["n", "v"], [["1", "1.5"], ["22", "22.25"], ["333", "-333.125"]], "lr"),
    "tofu_private": (["p"], [["\U0010fffd  x"]], "l"),
    "styles": (["h"], [[B1 + "bold" + B0 + " " + I1 + "ital" + I0 + " " + B1 + I1 + "bi" + I0 + B0], [B1 + "bold phrase that wraps across a few lines when the pane is narrow" + B0]], "l"),
    "styles_unmatched": (["h"], [[B1 + "never closed"], ["x" + I0 + B0 + " stray closers"]], "l"),
    "styles_cjk_emoji": (["h"], [[B1 + "太字😀bold" + B0 + I1 + "日本語 italic" + I0]], "c"),
    "nbsp_spaces": (["a b", "c"], [["x y  z", "  lead and trail  "]], "lr"),
    "tiny_pane_atoms": (["supercalifragilisticexpialidocious", "b"], [["x", "y"]], "lr"),
}
PANES = [250, 320, 447, 600, 788, 1200]


def covered(fonts, ch):
    """True if some font that this renderer would use draws a real glyph for ch (not .notdef)."""
    kind = T.kind_of(ch)
    face = fonts.face(kind, False, False)
    try:
        m = face.getmask(ch)
        nd = face.getmask("\U0010ffff") if kind != "emoji" else face.getmask("")
    except Exception:
        return False
    if ch.isspace() or ch in "‍️́̈̃":
        return True
    return not (m.size == nd.size and bytes(m) == bytes(nd))


def run():
    fonts = T.Fonts(16, 1)
    print("raqm layout:", features.check("raqm"), "| Pillow", __import__("PIL").__version__)
    bad = 0
    uncovered = {}
    refused = {}
    for name, (header, rows, al) in CASES.items():
        aligns = list(al[: len(header)]) + ["l"] * (len(header) - len(al))
        aligns = [{"l": "l", "r": "r", "c": "c"}[a] for a in aligns]
        for pane in PANES:
            tag = f"{name}@{pane}"
            try:
                img, placed, info = T.render(header, rows, aligns, pane, 1, 16, None)
            except T.ShapingNeeded as exc:
                refused.setdefault(name, str(exc))
                continue
            except Exception:
                print("CRASH", tag)
                traceback.print_exc()
                bad += 1
                continue
            probs = []
            if info["width"] > pane and not info["overflow"]:
                probs.append("wider than pane (%d>%d) without overflow flag" % (info["width"], pane))
            expect = [(ri + 1, ci, t) for ri, r in enumerate(rows) for ci, t in enumerate(r) if T.plain(t).strip()]
            res = T.self_check(img, placed, info, expect)
            probs += res["problems"]
            w = res["worst_ink_dev_px"]
            punct = any(ch in "「」『』（）、。，！？" for row in [header] + rows for t in row for ch in t)  # side bearing is the glyph's design
            if (w["l"] > 3 or w["r"] > 4 or w["c"] > 4) and not punct:
                if not info["overflow"]:
                    probs.append("alignment ink dev %s" % w)
            # ink must stay inside the picture
            bb = T.ink_bbox(img, (0, 0, img.width, img.height))
            if bb is None and expect:
                probs.append("blank picture")
            # ink of one cell must not spill into the gap/next column more than 2 px
            for p in placed:
                if not p["text"].strip():
                    continue
                box = (p["col_x"] - 12, p["top"], p["col_x"] + p["col_w"] + 12, p["top"] + info["lh"])
                bbx = T.ink_bbox(img, box)
                if bbx and (bbx[0] < p["col_x"] - 3 or bbx[2] > p["col_x"] + p["col_w"] + 3) and not info["overflow"]:
                    probs.append("cell %d,%d ink spills outside its column (%s vs %d..%d)" % (p["row"], p["col"], bbx, p["col_x"], p["col_x"] + p["col_w"]))
                    break
            for row in [header] + rows:
                for t in row:
                    for ch in T.plain(t):
                        if T.kind_of(ch) == "none":
                            uncovered.setdefault(name, set()).add("U+%04X" % ord(ch))
            if probs:
                bad += 1
                print("FAIL", tag, "|", "; ".join(probs[:3]))
    print()
    print("cases x panes:", len(CASES) * len(PANES), "failing:", bad)
    print("REFUSED (renderer says it cannot draw them faithfully; caller keeps text layout):")
    for k, v in refused.items():
        print("  ", k, "|", v)
    print("glyphs no font in the chain draws (would show as boxes):")
    for k, v in uncovered.items():
        print("  ", k, sorted(v)[:12])


if __name__ == "__main__":
    run()
