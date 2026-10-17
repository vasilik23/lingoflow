import shutil
import subprocess
from pathlib import Path

from django.test import SimpleTestCase


class ExamWritingResetTests(SimpleTestCase):
    def test_attempt_replacement_clears_transient_checks_and_ai_request_state(self):
        node = shutil.which('node')
        self.assertIsNotNone(node)
        root = Path(__file__).parent
        for script in ('test_exam_writing_reset.cjs', 'test_ai_writing_ui.cjs'):
            result = subprocess.run([node, str(root / script)], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
