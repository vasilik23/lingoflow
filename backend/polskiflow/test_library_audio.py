from hashlib import sha256
from pathlib import Path

from django.test import SimpleTestCase, TestCase

from polskiflow.domain.library_audio import audio_url, manifest
from polskiflow.domain.b1_weekly_mock import VARIANTS
from polskiflow.learning.models import ReadingText


class LibraryAudioTests(SimpleTestCase):
    def test_native_player_lifecycle(self):
        import subprocess
        result = subprocess.run(['node', str(Path(__file__).with_name('test_reading_file_audio.cjs'))],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_file_matches_manifest(self):
        root = Path(__file__).parent / 'learning/static'
        clips = manifest()
        self.assertEqual(len(clips), 73)
        self.assertEqual({str(path.relative_to(root)) for path in (root / 'polskiflow/audio/library').glob('*.m4a')},
                         {clip['path'] for clip in clips.values()})
        for clip in clips.values():
            data = (root / clip['path']).read_bytes()
            self.assertEqual(sha256(data).hexdigest(), clip['sha256'])
            self.assertIn(b'ftyp', data[:16])
            self.assertGreater(clip['duration_seconds'], 1)

    def test_b1_exact_transcript_and_stale_text(self):
        for variant in VARIANTS:
            self.assertIn('.m4a?v=', audio_url(f'b1-{variant.id}', variant.listening_transcript))
            self.assertIsNone(audio_url(f'b1-{variant.id}', variant.listening_transcript + ' changed'))
        self.assertIsNone(audio_url('missing', 'text'))


class ReadingAudioCoverageTests(TestCase):
    def test_all_migrated_readings_have_matching_audio(self):
        texts = ReadingText.objects.filter(is_active=True)
        self.assertEqual(texts.count(), 70)
        for text in texts:
            self.assertIsNotNone(audio_url(f'reading-{text.id}', ' '.join(text.paragraphs)), text.id)
