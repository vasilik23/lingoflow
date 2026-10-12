from hashlib import sha256
from pathlib import Path
from django.test import SimpleTestCase
from polskiflow.domain.practice_listening_media import practice_media, manifest
from polskiflow.domain.native_listening import LISTENING_DIALOGUE, LISTENING_B1, LISTENING_B2


class PracticeListeningMediaTests(SimpleTestCase):
    def test_all_current_web_and_native_transcripts_match_published_media(self):
        from polskiflow import auth_views
        root = Path(__file__).parent / 'learning/static'
        for name, content in [('dialogue', LISTENING_DIALOGUE), ('b1', LISTENING_B1), ('b2', LISTENING_B2)]:
            self.assertEqual(content['lines'], getattr(auth_views, 'LISTENING_' + ('DIALOGUE' if name == 'dialogue' else name.upper()))['lines'])
            paths = practice_media(name, content['lines'])
            self.assertIsNotNone(paths)
            for part, path in paths.items():
                clip = manifest()[f'{name}-{part}']
                data = (root / path).read_bytes()
                self.assertEqual(sha256(data).hexdigest(), clip['sha256'])
                self.assertIn(b'ftyp', data[:16])
                self.assertGreater(clip['duration_seconds'], 1)
        self.assertEqual(len(manifest()), 7)

    def test_changed_or_unknown_transcript_cannot_use_stale_audio(self):
        self.assertIsNone(practice_media('dialogue', ('Different text',)))
        self.assertIsNone(practice_media('unknown', LISTENING_B1['lines']))
