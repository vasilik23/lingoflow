"""Export original scripts and review requirements, without approving audio."""

import json
from django.core.management.base import BaseCommand
from polskiflow.domain.b1_listening_recordings import transcript_checksum
from polskiflow.domain.b1_weekly_mock import VARIANTS
from polskiflow.domain.b1_training_content import training_questions


class Command(BaseCommand):
    help = "Print the original B1 narration and review packet as JSON."

    def handle(self, *args, **options):
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
