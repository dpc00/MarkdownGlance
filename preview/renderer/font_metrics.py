"""The advance the preview's monospace font really has, on this host.

`tables.budgets` turns the preview's pixel width into a column count, and
`measure.outline_width_px` turns columns back into pixels. Both need the width
of one character, and the stylesheet leaves that to the host: `.md-table` names
DejaVu Sans Mono, then Liberation Mono, then Consolas, then `monospace`, and
which of those exists is a property of the machine. minihtml offers no way to
ask, so the advance is read from the font file the host will pick.

Pillow reads the file at a size large enough for the advance to be exact to
several places, and the result is kept as a fraction of the font size -- the
same shape `tables` used as a constant. Pillow is a Package Control library on
every platform the package supports, but this module is also imported by tests
and by a host where the library is not installed yet, so a missing Pillow, a
missing font, or a font Pillow cannot open falls back to the values measured on
Linux instead of raising.

Nothing is imported at plugin load (ADR 0012): resolving a font is a few
`isfile` calls, and Pillow is imported the first time an advance is asked for,
then cached. A preview that never draws a table or an outline never pays for it.

The stacks below mirror `resources/preview.css`, which stays the source of
truth for what the host is asked to draw.
"""

import os
import sys

from ..domain.paths import HOST

# Measured on ST 4200 (Linux, X11) for the fonts the Linux stack resolves.
FALLBACK_LATIN_ADVANCE = 0.6023  # DejaVu Sans Mono
FALLBACK_CJK_ADVANCE = 0.5  # Noto Sans Mono CJK

# `resources/preview.css`, `.md-table`.
MONO_STACK = ("DejaVu Sans Mono", "Liberation Mono", "Consolas")
# `resources/preview.css`, `.md-table-cjk`.
CJK_STACK = ("Noto Sans Mono CJK SC", "Sarasa Mono SC", "Noto Sans Mono CJK TC")

# A size large enough that the advance is a precise fraction of the em; the
# fraction, not the pixel width, is what the renderer keeps.
SAMPLE_SIZE = 1000

_FAMILY_FILES = {
    "DejaVu Sans Mono": (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        "/usr/local/share/fonts/DejaVuSansMono.ttf",
        "/opt/homebrew/share/fonts/DejaVuSansMono.ttf",
        "C:/Windows/Fonts/DejaVuSansMono.ttf",
        "/Library/Fonts/DejaVuSansMono.ttf",
        "/System/Library/Fonts/Supplemental/DejaVuSansMono.ttf",
        "~/Library/Fonts/DejaVuSansMono.ttf",
    ),
    "Liberation Mono": (
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/TTF/LiberationMono-Regular.ttf",
        "C:/Windows/Fonts/LiberationMono-Regular.ttf",
        "/Library/Fonts/LiberationMono-Regular.ttf",
        "~/Library/Fonts/LiberationMono-Regular.ttf",
    ),
    "Consolas": (
        "C:/Windows/Fonts/consola.ttf",
        "/Library/Fonts/Consolas.ttf",
        "/System/Library/Fonts/Supplemental/Consolas.ttf",
        "~/Library/Fonts/Consolas.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/Consolas.ttf",
    ),
    "Noto Sans Mono CJK SC": (
        "/usr/share/fonts/opentype/noto/NotoSansMonoCJKsc-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansMonoCJKsc-Regular.otf",
        "/usr/share/fonts/noto/NotoSansMonoCJKsc-Regular.otf",
        "/usr/local/share/fonts/NotoSansMonoCJKsc-Regular.otf",
    ),
    "Noto Sans Mono CJK TC": (
        "/usr/share/fonts/opentype/noto/NotoSansMonoCJKtc-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansMonoCJKtc-Regular.otf",
        "/usr/share/fonts/noto/NotoSansMonoCJKtc-Regular.otf",
    ),
    "Sarasa Mono SC": (
        "/usr/share/fonts/truetype/sarasa/SarasaMonoSC-Regular.ttf",
        "/usr/share/fonts/opentype/sarasa/SarasaMonoSC-Regular.ttf",
        "~/.local/share/fonts/SarasaMonoSC-Regular.ttf",
    ),
}

# `monospace` is the last name in `.md-table`, and what it resolves to is the
# host's default: Menlo on macOS, Consolas on Windows, DejaVu on Linux.
_GENERIC_MONO = {
    "darwin": (
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Supplemental/Menlo.ttc",
        "/Library/Fonts/Menlo.ttc",
    ),
    "win32": (
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/cour.ttf",
    ),
}
_GENERIC_MONO_OTHER = ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",)

# An advance outside these bounds is a font we did not mean to measure, or a
# value Pillow reported for a font it only partly understood.
_LATIN_BOUNDS = (0.3, 1.0)
_CJK_BOUNDS = (0.3, 1.5)


def _existing(paths):
    for raw in paths:
        path = HOST.expand(raw)
        if os.path.isfile(path):
            return path
    return None


def resolve(families, generic=False):
    """The first font file in `families` that this host has, or None.

    `generic` asks for the host's `monospace` face when none of the named
    families is installed, which is what the stylesheet falls through to.
    """
    for family in families:
        path = _existing(_FAMILY_FILES.get(family, ()))
        if path is not None:
            return path
    if generic:
        return _existing(_GENERIC_MONO.get(sys.platform, _GENERIC_MONO_OTHER))
    return None


def advance(path, sample, size=SAMPLE_SIZE):
    """Width of one glyph as a fraction of the font size, or None.

    The advance of a monospace face is the same for every Latin glyph, so one
    sample is enough; the CJK face is sampled with a wide character, which is
    the width a table counts as two columns.
    """
    if path is None:
        return None
    try:
        from PIL import ImageFont

        font = ImageFont.truetype(path, size)
        return font.getlength(sample) / size
    except Exception:  # no Pillow, or a file Pillow cannot read
        return None


def _measured(path, sample, fallback, bounds):
    value = advance(path, sample)
    if value is not None and bounds[0] <= value <= bounds[1]:
        return value
    return fallback


LATIN_FONT = resolve(MONO_STACK, generic=True)
CJK_FONT = resolve(CJK_STACK)

# Measured once, on first use, so that a host with no tables and no outline
# never imports Pillow at all.
_MEASURED = {}


def _cached(key, path, sample, fallback, bounds):
    if key not in _MEASURED:
        _MEASURED[key] = _measured(path, sample, fallback, bounds)
    return _MEASURED[key]


def latin_advance():
    """One Latin character in the table font, as a fraction of the font size."""
    return _cached("latin", LATIN_FONT, "M", FALLBACK_LATIN_ADVANCE, _LATIN_BOUNDS)


def cjk_advance():
    """One wide character in the CJK font, as a fraction of the font size."""
    return _cached("cjk", CJK_FONT, "\u4e2d", FALLBACK_CJK_ADVANCE, _CJK_BOUNDS)


def cjk_ships():
    """Whether the CJK stack's fonts are installed, so a CJK table gets one.

    A font that ships is a font that draws two-column characters, whether or
    not Pillow is here to measure it; only its advance needs the fallback.
    """
    return CJK_FONT is not None
