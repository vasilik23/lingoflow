"""Export original scripts and review requirements, without approving audio."""

import json
from django.core.management.base import BaseCommand
from polskiflow.domain.b1_listening_recordings import transcript_checksum
from polskiflow.domain.b1_weekly_mock import VARIANTS
from polskiflow.domain.b1_training_content import training_questions


class Command(BaseCommand):
    help = "Print the original B1 narration and review packet as JSON."

    def add_arguments(self, parser):
        parser.add_argument("--expanded", action="store_true", help="Export staged four-block narration; not active in guided runs.")

    def handle(self, *args, **options):
        if options["expanded"]:
            self.stdout.write(json.dumps(self.expanded_packet(), ensure_ascii=False, indent=2))
            return
        self.stdout.write(json.dumps({
            "created_for": "PolskiFlow", "origin": "original", "status": "awaiting_recording_and_review",
            "instructions": [
                "Read the exact Polish transcript, without adding an introduction or reading questions.",
                "Use a natural, clear pace; retain all dates, numbers and correction phrases.",
                "Deliver MP3, OGG or WAV without music, clipping or long leading/trailing silence.",
                "Confirm redistribution rights for the voice and recording separately from the original text.",
                "Have a Polish-speaking reviewer listen to the entire file and check every answer against it.",
                "Record source, author, license URL, changes, reviewer, review date and final file SHA-256.",
                "Add reviewed immutable files and metadata to b1_listening_recordings.RECORDINGS; run Django check.",
            ],
            "variants": [{
                "id": variant.id, "transcript": variant.listening_transcript,
                "transcript_sha256": transcript_checksum(variant.listening_transcript),
                "answer_checks": [{"id": q.id, "question": q.prompt,
                    "correct_answer": q.options[q.correct], "explanation": q.explanation}
                    for q in training_questions(variant, "listening")],
            } for variant in VARIANTS],
        }, ensure_ascii=False, indent=2))

    def expanded_packet(self):
        from polskiflow.domain.b1_training_listening_draft import LISTENING_DRAFTS
        variants = []
        for variant in VARIANTS:
            blocks = [{
                "id": "variant", "title": variant.label, "genre": "short_message",
                "transcript": variant.listening_transcript,
                "transcript_sha256": transcript_checksum(variant.listening_transcript),
                "voice_notes": "One voice. Read only the exact transcript, not questions or titles.",
                "answer_checks": self.answer_checks(training_questions(variant, "listening", 9)),
            }]
            blocks.extend({
                "id": block.id, "title": block.title, "genre": block.genre,
                "transcript": block.transcript, "transcript_sha256": transcript_checksum(block.transcript),
                "voice_notes": block.voice_notes, "answer_checks": self.answer_checks(block.questions),
            } for block in LISTENING_DRAFTS)
            variants.append({"id": variant.id, "blocks": blocks, "answer_count": 20})
        return {
            "created_for": "PolskiFlow", "origin": "original", "verified_at": "2026-10-06",
            "review_scope": "internal text review only; independent Polish review pending",
            "format": "expanded-draft-v1", "status": "awaiting_recording_and_review",
            "enabled_in_guided_run": False,
            "instructions": [
                "Record each block separately; read the exact Polish transcript, never titles, questions or voice notes.",
                "For dialogues and interviews alternate voices at blank lines. Preserve all numbers, corrections and negations.",
                "Use a natural clear pace. Text ownership does not establish rights to a narrator voice or recording.",
                "Deliver rights-cleared MP3, OGG or WAV with author, license URL, reviewer, date and final file SHA-256.",
                "A Polish-speaking reviewer must listen to every complete file and verify all correct and incorrect options.",
                "The three extension blocks are shared across variants: record each once, retain its checksum and immutable ID.",
                "Register reviewed immutable BlockRecording entries in BLOCK_RECORDINGS, not the legacy RECORDINGS registry. A complete four-block collection enables pinned version-10 playback; partial collections remain disabled.",
                "Do not claim full exam equivalence until duration, difficulty and formats are independently validated.",
            ], "variants": variants,
        }

    @staticmethod
    def answer_checks(questions):
        return [{"id": q.id, "question": q.prompt, "options": list(q.options),
                 "correct_index": q.correct, "correct_answer": q.options[q.correct],
                 "explanation": q.explanation} for q in questions]
