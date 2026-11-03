"""The font advance the renderer budgets with is measured, not assumed."""

import os.path
import sys
import unittest
from unittest import mock

from MarkdownGlance.preview.renderer import font_metrics
from MarkdownGlance.preview.renderer.font_metrics import (
    CJK_FONT,
    FALLBACK_CJK_ADVANCE,
    FALLBACK_LATIN_ADVANCE,
    LATIN_FONT,
    MONO_STACK,
    cjk_advance,
    cjk_ships,
    latin_advance,
)

# What `monospace` resolves to on each host when no named family is installed.
GENERIC_FILES = {
    "win32": ("consola.ttf", "cour.ttf"),
    "darwin": ("menlo.ttc",),
}
LINUX_FILES = ("dejavusansmono.ttf",)


class AdvanceTest(unittest.TestCase):
    def test_the_advance_is_a_plausible_fraction_of_the_em(self):
        for value in (latin_advance(), cjk_advance()):
            self.assertGreaterEqual(value, 0.3, value)
            self.assertLessEqual(value, 1.0, value)

    def test_a_measured_advance_wins_over_the_fallback(self):
        with mock.patch.object(font_metrics, "advance", return_value=0.55):
            self.assertEqual(
                font_metrics._measured("ignored", "M", 0.6023, (0.3, 1.0)),
                0.55,
            )

    def test_an_impossible_advance_is_ignored(self):
        for value in (0.0, 0.01, 5.0):
            with mock.patch.object(font_metrics, "advance", return_value=value):
                self.assertEqual(
                    font_metrics._measured("ignored", "M", 0.6023, (0.3, 1.0)),
                    0.6023,
                    value,
                )

    def test_no_font_or_no_pillow_means_no_measurement(self):
        # `advance(None, ...)` is a host without the font; a Pillow that is not
        # installed raises on import, which is caught the same way.
        self.assertIsNone(font_metrics.advance(None, "M"))
        with mock.patch.dict(sys.modules, {"PIL": None, "PIL.ImageFont": None}):
            self.assertIsNone(font_metrics.advance("ignored", "M"))

    def test_the_font_is_measured_once(self):
        try:
            with mock.patch.object(
                font_metrics, "advance", return_value=0.55
            ) as measured:
                font_metrics._MEASURED.clear()
                self.assertEqual(latin_advance(), 0.55)
                self.assertEqual(latin_advance(), 0.55)
                self.assertEqual(measured.call_count, 1)
        finally:
            font_metrics._MEASURED.clear()

    def test_the_fallback_is_the_linux_measurement(self):
        self.assertEqual(FALLBACK_LATIN_ADVANCE, 0.6023)
        self.assertEqual(FALLBACK_CJK_ADVANCE, 0.5)

    def test_cjk_is_budgeted_only_when_its_font_is_installed(self):
        self.assertEqual(cjk_ships(), font_metrics.CJK_FONT is not None)


class RegistryTest(unittest.TestCase):
    """A font installed for one user is registered in HKCU, not under C:\\Windows."""

    def _fonts(self, entries):
        with mock.patch.object(font_metrics.os.path, "isfile", return_value=True):
            return font_metrics._fonts_from_entries(entries)

    def test_a_face_name_yields_its_family(self):
        fonts = self._fonts(
            [
                ("DejaVu Sans Mono Bold (TrueType)", r"C:\f\DejaVuSansMono-Bold.ttf"),
                ("DejaVu Sans Mono (TrueType)", r"C:\f\DejaVuSansMono.ttf"),
            ]
        )
        self.assertEqual(fonts["DejaVu Sans Mono"], r"C:\f\DejaVuSansMono.ttf")
        self.assertNotIn("DejaVu Sans Mono Bold", fonts)

    def test_a_regular_face_wins_whichever_order_it_is_registered_in(self):
        fonts = self._fonts(
            [
                ("Consolas (TrueType)", r"C:\f\consola.ttf"),
                ("Consolas Bold (TrueType)", r"C:\f\consolab.ttf"),
            ]
        )
        self.assertEqual(fonts["Consolas"], r"C:\f\consola.ttf")

    def test_a_registry_name_that_ends_in_a_style_word(self):
        # Windows registers Noto's regular face with "Regular" in the name.
        fonts = self._fonts(
            [("Noto Sans Mono CJK SC Regular (OpenType)", r"C:\f\Noto.otf")]
        )
        self.assertEqual(fonts["Noto Sans Mono CJK SC"], r"C:\f\Noto.otf")

    def test_a_registered_file_that_is_gone_is_skipped(self):
        self.assertEqual(
            font_metrics._fonts_from_entries([("Ghost (TrueType)", r"C:\nope\x.ttf")]),
            {},
        )

    def test_the_registry_is_asked_before_the_built_in_paths(self):
        with mock.patch.object(
            font_metrics, "_registry_fonts", return_value={"Consolas": __file__}
        ):
            with mock.patch.dict(
                font_metrics._FAMILY_FILES, {"Consolas": ("C:/nope.ttf",)}, clear=True
            ):
                self.assertEqual(font_metrics._installed("Consolas"), __file__)

    def test_a_family_the_registry_does_not_name_falls_back_to_the_paths(self):
        with mock.patch.object(font_metrics, "_registry_fonts", return_value={}):
            with mock.patch.dict(
                font_metrics._FAMILY_FILES, {"Consolas": (__file__,)}, clear=True
            ):
                self.assertEqual(font_metrics._installed("Consolas"), __file__)


class ResolveTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(font_metrics, "_registry_fonts", return_value={})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_first_installed_family_wins(self):
        with mock.patch.dict(
            font_metrics._FAMILY_FILES,
            {"DejaVu Sans Mono": (__file__,), "Consolas": (__file__,)},
            clear=True,
        ):
            self.assertEqual(font_metrics.resolve(MONO_STACK), __file__)
        with mock.patch.dict(
            font_metrics._FAMILY_FILES,
            {"Liberation Mono": (__file__,), "Consolas": (__file__)},
            clear=True,
        ):
            self.assertEqual(font_metrics.resolve(MONO_STACK), __file__)

    def test_no_named_family_falls_through_to_the_generic_font(self):
        with mock.patch.dict(font_metrics._FAMILY_FILES, {}, clear=True):
            self.assertIsNone(font_metrics.resolve(MONO_STACK))
            with mock.patch.dict(
                font_metrics._GENERIC_MONO, {"win32": (__file__,)}, clear=True
            ):
                with mock.patch.object(sys, "platform", "win32"):
                    self.assertEqual(
                        font_metrics.resolve(MONO_STACK, generic=True), __file__
                    )

    def test_the_resolved_font_is_one_the_stylesheet_names(self):
        if LATIN_FONT is None:
            # A host with none of the stack and no generic font to fall back
            # to: the budget is the Linux constant, which is all it can be.
            self.assertEqual(latin_advance(), FALLBACK_LATIN_ADVANCE)
            return
        name = os.path.basename(LATIN_FONT).lower()
        # Every name in the stylesheet's stack, whichever host supplies it:
        # DejaVu and Liberation can be installed by hand on Windows too.
        expected = (
            "dejavusansmono.ttf",
            "liberationmono-regular.ttf",
            "consola.ttf",
            "cour.ttf",
            "menlo.ttc",
        )
        self.assertIn(name, expected)


class AdvanceMatchesTheDrawnFontTest(unittest.TestCase):
    def test_the_advance_comes_from_the_resolved_font(self):
        if LATIN_FONT is None:
            self.skipTest("no font to measure")
        measured = font_metrics.advance(LATIN_FONT, "M")
        if measured is None:
            self.skipTest("Pillow is not installed")
        self.assertEqual(latin_advance(), measured)

    def test_the_cjk_advance_is_one_column_not_two(self):
        # A wide character is two columns; the budget needs the column.
        if CJK_FONT is None:
            self.skipTest("no CJK font installed")
        column = font_metrics.advance(CJK_FONT, "M")
        wide = font_metrics.advance(CJK_FONT, "\u4e2d")
        if column is None or wide is None:
            self.skipTest("Pillow is not installed")
        self.assertAlmostEqual(cjk_advance(), column, places=3)
        self.assertAlmostEqual(wide, column * 2, places=2)


if __name__ == "__main__":
    unittest.main()
