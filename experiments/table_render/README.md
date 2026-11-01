# Tables drawn as images (experiment, not a PR)

Branch `table-images-experiment` of a fork of feibuilds/MarkdownGlance, based on tag 0.7.0 (590bcc0).
Purpose: see whether a markdown table can be shown in the preview as a picture drawn from
**measured font glyphs**, so alignment no longer depends on counting characters. The editor tab keeps
the user's plain pipe table; only the preview changes. Nothing here has been proposed upstream.

## How it works
- `preview/renderer/tables.py`: before the existing monospace layout, `_image_table()` sends the table
  (cells flattened to text, bold/italic as zero-width markers, alignments, pane width in pixels) to a
  helper process and receives a PNG. If the helper fails or refuses, the old layout is used unchanged.
- `preview/renderer/structure.py`: passes the preview width in pixels to `tables.py`.
- `preview/renderer/minihtml.py`: emits the image with its pixel size. minihtml draws every image
  4 px taller than its height attribute, so the height attribute is set 4 px smaller (`TABLE_IMG_ADJ`).
- `experiments/table_render/table_render.py`: the renderer (Pillow). Measures every run with the font
  file that draws it (Consolas, Segoe UI, Segoe UI Symbol, Microsoft YaHei, Malgun Gothic, Segoe UI
  Emoji), sizes columns in whole pixels (only the widest columns shrink), wraps by pixel width,
  aligns every line from its own measured width, breaks over-long words anywhere.
- `table_render_cli.py`: stdin JSON in, `W H\n` + PNG bytes out; exit code 3 = refused.

## Tests
`python -I stress_test.py` renders 26 odd tables at 6 pane widths (250 to 1200 px) and checks from the
picture: no crash, every cell has ink, alignment ink within a few px, no spill into a neighbouring column,
no table wider than the pane. Latest run: 156 combinations, 0 failures, 6 cases refused on purpose.
`contact_sheet.py` builds a picture of chosen cases for looking at. `demo.md` is the manual demo
(run "MarkdownGlance: open side by side"; checked at 1936, 1179 and 900 px windows).

## Refused on purpose (the package keeps its old text layout for that table)
Scripts and sequences that need a shaping engine (Arabic, Hebrew, Indic, Thai, Khmer, Myanmar), ZWJ
emoji sequences, flags, skin tones, combining marks with no precomposed form, and characters no font
in the chain has. Pillow here has no raqm, so these cannot be drawn faithfully.

## Known limits
- Windows only (font paths); needs a Python with Pillow (`MDGLANCE_TABLE_PYTHON` overrides the path).
  Pillow inside Sublime's own plugin host is untested; the helper process avoids the question.
- Colours are hard-coded to the current dark scheme; scale is 1x only; no hi-dpi.
- Inline code, links, strikethrough and images inside cells are drawn as plain text.
- CJK and symbols have no italic (upright).
- The +4 px image stretch is compensated, not explained, and not measured pixel by pixel.
- Selecting or copying text from a table in the preview is impossible (it is a picture).
