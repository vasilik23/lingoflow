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


@dataclass(frozen=True)
class BlockRecording(ListeningRecording):
    block_id: str


# Shared extension files use variant_id='*'; original messages use exact variants.
BLOCK_RECORDINGS: tuple[BlockRecording, ...] = ()


def expanded_listening_blocks(variant):
    from polskiflow.domain.b1_training_listening_draft import ListeningDraft, LISTENING_DRAFTS
    from polskiflow.domain.b1_exam_simulation import simulation_questions
    first = ListeningDraft('variant', variant.label, 'short_message', variant.listening_transcript,
                           simulation_questions(variant, 'listening'), 'One voice.')
    return (first, *LISTENING_DRAFTS)


def expected_block_transcript(item):
    from polskiflow.domain.b1_training_listening_draft import LISTENING_DRAFTS
    from polskiflow.domain.b1_weekly_mock import get_mock_variant
    if item.block_id == 'variant':
        variant = get_mock_variant(item.variant_id)
        return variant.listening_transcript if variant else None
    if item.variant_id != '*':
        return None
    return next((b.transcript for b in LISTENING_DRAFTS if b.id == item.block_id), None)


def block_recordings_for_variant(variant):
    selected = {}
    for block in expanded_listening_blocks(variant):
        scope = variant.id if block.id == 'variant' else '*'
        recording = next((r for r in reversed(BLOCK_RECORDINGS) if r.block_id == block.id
                          and r.variant_id == scope
                          and r.transcript_sha256 == transcript_checksum(block.transcript)), None)
        if not recording:
            return {}  # An incomplete collection never enables a new run.
        selected[block.id] = recording.id
    return selected


def block_recordings_for_run(state, variant):
    pinned = state.get('listening_recording_ids', {})
    result = []
    for block in expanded_listening_blocks(variant):
        scope = variant.id if block.id == 'variant' else '*'
        recording = next((r for r in BLOCK_RECORDINGS if r.id == pinned.get(block.id)
                          and r.block_id == block.id and r.variant_id == scope
                          and r.transcript_sha256 == transcript_checksum(block.transcript)), None)
        result.append({'block': block, 'recording': recording, 'missing': recording is None})
    return tuple(result)
