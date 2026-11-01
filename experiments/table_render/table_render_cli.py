"""Helper process for the table-as-image demo.

stdin : JSON {"header": [...], "rows": [[...]], "aligns": ["l","r","c"], "pane": 788}
stdout: one text line "WIDTH HEIGHT\n" followed by the PNG bytes.
Runs on the system Python (Pillow); Sublime's plugin host does not have to.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import table_render  # noqa: E402


def main():
    spec = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    try:
        img, placed, info = table_render.render(spec["header"], spec["rows"], spec["aligns"], int(spec["pane"]), 1, 16, None)
    except table_render.ShapingNeeded as exc:
        sys.stderr.write(str(exc) + "\n")
        sys.exit(3)  # the caller keeps its own text layout for this table
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    out = sys.stdout.buffer
    out.write(("%d %d\n" % (info["width"], info["height"])).encode("ascii"))
    out.write(buf.getvalue())
    out.flush()


if __name__ == "__main__":
    main()
