"""Synthetic AAC files: serve only an exact match to the displayed source text."""
import json
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from django.templatetags.static import static


@lru_cache(maxsize=1)
def manifest():
    return json.loads(Path(__file__).with_suffix('.json').read_text(encoding='utf-8'))['clips']


def audio_url(identifier, transcript):
    clip = manifest().get(f'{identifier}-full')
    if not clip or clip['transcript_sha256'] != sha256(transcript.encode('utf-8')).hexdigest():
        return None
    return static(clip['path']) + '?v=' + clip['sha256'][:12]
