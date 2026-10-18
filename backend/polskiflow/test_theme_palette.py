"""The agreed palette must retain readable semantic foreground/background pairs."""
import re
from pathlib import Path

from django.test import SimpleTestCase

CSS = Path(__file__).parent / 'learning/static/polskiflow/app.css'


def luminance(color):
    rgb = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4 for value in rgb]
    return sum(value * weight for value, weight in zip(linear, (.2126, .7152, .0722)))


def contrast(first, second):
    values = sorted((luminance(first), luminance(second)))
    return (values[1] + .05) / (values[0] + .05)


def palette(dark=False):
    css = CSS.read_text()
    light = re.search(r':root \{([^}]+)\}', css).group(1)
    theme = re.search(r':root\[data-theme="dark"\] \{([^}]+)\}', css).group(1) if dark else ''
    values = dict(re.findall(r'(--[\w-]+):\s*([^;]+);', light + theme))
    def resolve(name):
        value = values[name]
        return resolve(value[4:-1]) if value.startswith('var(') else value
    return {name: resolve(name) for name in values}


class ThemePaletteTests(SimpleTestCase):
    def test_exact_agreed_light_and_dark_semantic_colors(self):
        names = ('--bg', '--surface', '--text', '--muted', '--primary', '--on-action', '--primary-soft', '--line', '--red')
        colors = (
            ('#F7F8F5', '#FFFFFF', '#202923', '#626E66', '#25634F', '#FFFFFF', '#EAF3EE', '#DFE5DF', '#B33D49'),
            ('#141A17', '#1D2621', '#EDF2EE', '#ACB9AF', '#8ED5B2', '#14251C', '#283F32', '#39483E', '#FFABB3'),
        )
        for dark, expected in enumerate(colors):
            with self.subTest(dark=bool(dark)):
                actual = palette(bool(dark))
                self.assertEqual(tuple(actual[name] for name in names), expected)

    def test_body_muted_action_selected_error_and_focus_contrast(self):
        for dark in (False, True):
            values = palette(dark)
            pairs = [(foreground, background) for foreground in ('--text', '--muted')
                     for background in ('--bg', '--surface', '--primary-soft')]
            pairs += [('--on-action', '--primary'), ('--on-action', '--action-hover'),
                      ('--red', '--red-soft'), ('--on-danger', '--red')]
            for foreground, background in pairs:
                with self.subTest(dark=dark, foreground=foreground, background=background):
                    self.assertGreaterEqual(contrast(values[foreground], values[background]), 4.5)
            for foreground in ('--control-border', '--focus'):
                for background in ('--surface', '--bg'):
                    with self.subTest(dark=dark, foreground=foreground, background=background):
                        self.assertGreaterEqual(contrast(values[foreground], values[background]), 3)

    def test_component_styles_do_not_introduce_another_literal_palette_or_gradients(self):
        components = CSS.read_text().split('* { box-sizing', 1)[1]
        self.assertNotRegex(components, r'#[0-9a-fA-F]{3,8}\b')
        self.assertNotRegex(components, r'(linear|radial|conic)-gradient\(')

    def test_standalone_offline_and_editorial_use_the_same_semantic_tokens(self):
        templates = Path(__file__).parent.parent / 'templates'
        names = ('--bg', '--surface', '--text', '--muted', '--line', '--primary', '--on-action', '--primary-soft', '--red')
        for path in ('offline.html', 'editorial/pilot_review.html'):
            blocks = re.findall(r':root(?:\[data-theme="dark"\])?\s*\{([^}]+)\}', (templates / path).read_text())
            self.assertEqual(len(blocks), 2)
            for dark, block in enumerate(blocks):
                values = dict(re.findall(r'(--[\w-]+):\s*([^;\s}]+)', block))
                expected = palette(bool(dark))
                for name in names:
                    with self.subTest(path=path, dark=bool(dark), name=name):
                        self.assertEqual(values[name], expected[name])
