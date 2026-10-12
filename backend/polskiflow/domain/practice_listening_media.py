"""Generated practice clips, matched to the exact current Polish transcript."""
import json
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

MANIFEST = Path(__file__).with_suffix('.json')


@lru_cache(maxsize=1)
def manifest():
    return json.loads(MANIFEST.read_text(encoding='utf-8'))['clips']


def practice_media(name, lines):
    clips = manifest()
    texts = {'full': ' '.join(lines)}
    if name == 'dialogue':
        texts.update({f'fragment-{index}': line for index, line in enumerate(lines)})
    result = {}
    for part, text in texts.items():
        clip = clips.get(f'{name}-{part}')
        if not clip or clip['transcript_sha256'] != sha256(text.encode('utf-8')).hexdigest():
            return None
        result[part] = clip['path']
    return result
