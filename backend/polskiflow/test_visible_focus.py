import shutil
import subprocess
from pathlib import Path

from django.test import SimpleTestCase


class VisibleFocusTests(SimpleTestCase):
    def test_keyboard_correction_preserves_focus_and_skips_sidebar_dialog_and_stale_targets(self):
        node = shutil.which('node')
        self.assertIsNotNone(node)
        result = subprocess.run([node, str(Path(__file__).with_suffix('.cjs'))], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
