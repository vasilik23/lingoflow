import json
from dataclasses import replace
from hashlib import sha256
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase

from polskiflow.domain.b1_listening_recordings import ListeningRecording, recording_for_run, recording_for_variant, transcript_checksum
from polskiflow.domain.b1_weekly_mock import VARIANTS
from polskiflow.learning.recording_checks import check_b1_recordings


class B1RecordingChecksTests(SimpleTestCase):
    def setUp(self):
        self.variant = VARIANTS[0]
        self.file = b"test audio bytes"
        self.item = ListeningRecording(
            "b1-v1-reviewed-1", self.variant.id, "polskiflow/audio/b1/v1-reviewed-1.mp3",
            sha256(self.file).hexdigest(), transcript_checksum(self.variant.listening_transcript),
            "Warsztaty", "Test narrator", "CC-BY-4.0", "https://creativecommons.org/licenses/by/4.0/",
            "https://example.org/audio", "None", "Test reviewer", "2026-10-05",
        )

    def check(self, items):
        with TemporaryDirectory() as directory:
            audio = Path(directory) / "clip.mp3"
            audio.write_bytes(self.file)
            with patch("polskiflow.domain.b1_listening_recordings.RECORDINGS", items), patch(
                "polskiflow.learning.recording_checks.finders.find", return_value=str(audio)
            ):
                return check_b1_recordings(None)

    def test_empty_registry_keeps_system_voice(self):
        self.assertIsNone(recording_for_variant(self.variant))
        self.assertEqual(check_b1_recordings(None), [])

    def test_reviewed_file_and_metadata_pass(self):
        self.assertEqual(self.check((self.item,)), [])

    def test_changed_audio_or_transcript_fails(self):
        for field in ("sha256", "transcript_sha256"):
            self.assertEqual(self.check((replace(self.item, **{field: "0" * 64}),))[0].id, "learning.E001")

    def test_missing_metadata_unsafe_urls_and_paths_fail(self):
        for fields in ({"author": ""}, {"reviewed_by": ""}, {"verified_at": "invalid"},
                       {"source_url": "javascript:alert(1)"}, {"license_url": "http://example.org"},
                       {"static_path": "polskiflow/audio/b1/../unreviewed.mp3"},
                       {"license": "CC-BY-NC-4.0"}):
            self.assertTrue(self.check((replace(self.item, **fields),)), fields)

    def test_duplicate_ids_and_paths_fail(self):
        self.assertTrue(self.check((self.item, self.item)))

    def test_missing_file_fails(self):
        with patch("polskiflow.domain.b1_listening_recordings.RECORDINGS", (self.item,)), patch(
            "polskiflow.learning.recording_checks.finders.find", return_value=None
        ):
            self.assertTrue(check_b1_recordings(None))

    def test_runs_pin_recordings_and_old_runs_keep_system_voice(self):
        new = replace(self.item, id="b1-v1-reviewed-2", static_path="polskiflow/audio/b1/v1-reviewed-2.mp3")
        self.assertEqual(self.check((self.item, new)), [])
        with patch("polskiflow.domain.b1_listening_recordings.RECORDINGS", (self.item, new)):
            self.assertEqual(recording_for_variant(self.variant), new)
            self.assertIsNone(recording_for_run({}, self.variant))
            self.assertEqual(recording_for_run({"listening_recording_id": self.item.id}, self.variant), self.item)
            self.assertIsNone(recording_for_run({"listening_recording_id": self.item.id}, VARIANTS[1]))

    def test_narration_packet_preserves_exact_text_and_answer_checks(self):
        output = StringIO()
        call_command("b1_recording_packet", stdout=output)
        packet = json.loads(output.getvalue())
        self.assertEqual(packet["status"], "awaiting_recording_and_review")
        self.assertEqual(len(packet["variants"]), 3)
        for variant, item in zip(VARIANTS, packet["variants"]):
            self.assertEqual(item["transcript"], variant.listening_transcript)
            self.assertEqual(item["transcript_sha256"], transcript_checksum(variant.listening_transcript))
            self.assertEqual(len(item["answer_checks"]), 5)

    def test_expanded_packet_has_reviewable_blocks_without_enabling_audio(self):
        from polskiflow.domain.b1_training_listening_draft import LISTENING_DRAFTS
        output = StringIO()
        call_command('b1_recording_packet', expanded=True, stdout=output)
        packet = json.loads(output.getvalue())
        self.assertFalse(packet['enabled_in_guided_run'])
        self.assertEqual(packet['status'], 'awaiting_recording_and_review')
        self.assertEqual(packet['origin'], 'original')
        for variant, item in zip(VARIANTS, packet['variants']):
            self.assertEqual(len(item['blocks']), 4)
            self.assertEqual(item['answer_count'], 20)
            self.assertEqual(item['blocks'][0]['transcript'], variant.listening_transcript)
            checks = [q for b in item['blocks'] for q in b['answer_checks']]
            self.assertEqual(len(checks), 20)
            self.assertEqual(len({q['id'] for q in checks}), 20)
            for block in item['blocks']:
                self.assertEqual(block['transcript_sha256'], transcript_checksum(block['transcript']))
                self.assertEqual(len(block['answer_checks']), 5)
                for q in block['answer_checks']:
                    self.assertEqual(q['correct_answer'], q['options'][q['correct_index']])
            for draft, block in zip(LISTENING_DRAFTS, item['blocks'][1:]):
                self.assertEqual(block['transcript'], draft.transcript)
                self.assertEqual(block['voice_notes'], draft.voice_notes)
        self.assertEqual(packet['variants'][0]['blocks'][1:], packet['variants'][2]['blocks'][1:])

    def test_expanded_packet_artifact_is_current_and_legacy_packet_stays_compatible(self):
        from pathlib import Path
        from polskiflow.domain.b1_training_content import CONTENT_VERSION, training_questions
        output = StringIO()
        call_command('b1_recording_packet', expanded=True, stdout=output)
        artifact = Path(__file__).resolve().parents[2] / 'docs/b1-expanded-recording-packet.json'
        self.assertEqual(json.loads(artifact.read_text()), json.loads(output.getvalue()))
        self.assertEqual(CONTENT_VERSION, 9)
        self.assertTrue(all(len(training_questions(v, 'listening')) == 5 for v in VARIANTS))
