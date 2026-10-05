"""Reviewed recordings only; IDs and filenames are immutable after publication."""

from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class ListeningRecording:
    id: str
    variant_id: str
    static_path: str
    sha256: str
    transcript_sha256: str
    title: str
    author: str
    license: str
    license_url: str
    source_url: str
    changes: str
    reviewed_by: str
    verified_at: str


# Populate only after rights and the complete spoken transcript are reviewed.
# Empty deliberately: no external candidate has yet passed those checks.
RECORDINGS: tuple[ListeningRecording, ...] = ()


def transcript_checksum(text):
    return sha256(text.encode("utf-8")).hexdigest()


def recording_for_variant(variant):
    return next((item for item in reversed(RECORDINGS) if item.variant_id == variant.id
                 and item.transcript_sha256 == transcript_checksum(variant.listening_transcript)), None)


def recording_for_run(state, variant):
    return next((item for item in RECORDINGS if item.id == state.get("listening_recording_id")
                 and item.variant_id == variant.id
                 and item.transcript_sha256 == transcript_checksum(variant.listening_transcript)), None)
