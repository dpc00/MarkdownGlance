"""The font advance the renderer budgets with is measured, not assumed."""

import os.path
import sys
import unittest
from unittest import mock

from MarkdownGlance.preview.renderer import font_metrics
from MarkdownGlance.preview.renderer.font_metrics import (
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


class ResolveTest(unittest.TestCase):
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
        expected = GENERIC_FILES.get(sys.platform, LINUX_FILES)
        self.assertIn(name, tuple(n.lower() for n in expected))

    def test_windows_measures_consolas_rather_than_the_linux_constant(self):
        # Consolas is 0.55 em where DejaVu Sans Mono is 0.6023, so a budget
        # built on the Linux constant leaves a Windows table about a tenth of
        # the width the preview could give it.
        if not sys.platform.startswith("win"):
            self.skipTest("only Windows ships Consolas")
        self.assertIsNotNone(LATIN_FONT)
        self.assertNotEqual(latin_advance(), FALLBACK_LATIN_ADVANCE)


if __name__ == "__main__":
    unittest.main()
