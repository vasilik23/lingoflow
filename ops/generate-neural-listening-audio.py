"""Offline practice audio generation; Piper/model are not production dependencies."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import date
import wave


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('transcripts', type=Path)
    parser.add_argument('model', type=Path)
    parser.add_argument('--runtime-dir', type=Path)
    args = parser.parse_args()
    if args.runtime_dir:
        sys.path.insert(0, str(args.runtime_dir))
    from piper import PiperVoice, SynthesisConfig
    inputs = json.loads(args.transcripts.read_text(encoding='utf-8'))
    if set(inputs) != {'dialogue', 'b1', 'b2'} or any(
        not isinstance(lines, list) or not lines or any(not isinstance(line, str) or not line.strip() for line in lines)
        for lines in inputs.values()
    ):
        parser.error('Expected nonempty dialogue/b1/b2 transcript arrays')
    voice = PiperVoice.load(str(args.model))
    root = Path(__file__).resolve().parents[1] / 'backend/polskiflow'
    output_dir = root / 'learning/static/polskiflow/audio/practice'
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        'engine': f'Piper {importlib.metadata.version("piper-tts")}',
        'voice': 'pl_PL-bass-high', 'model_source': 'https://huggingface.co/blackbartblues/piper-pl-bass-high',
        'model_revision': 'd38fb15ed4eec60c124e3da1fd67359af771c3dc',
        'model_license': 'Apache-2.0 (publisher declaration)',
        'model_sha256': hashlib.sha256(args.model.read_bytes()).hexdigest(),
        'created_at': date.today().isoformat(), 'origin': 'original', 'created_for': 'LingoFlow',
        'verification': 'exact transcript input and media decode; independent pronunciation review pending',
        'clips': {},
    }
    with tempfile.TemporaryDirectory(prefix='lingoflow-neural-audio-') as workdir:
        for name, lines in inputs.items():
            texts = {'full': ' '.join(lines)}
            if name == 'dialogue':
                texts.update({f'fragment-{index}': line for index, line in enumerate(lines)})
            for part, text in texts.items():
                identifier = f'{name}-{part}'
                wav_path = Path(workdir) / f'{identifier}.wav'
                with wave.open(str(wav_path), 'wb') as output:
                    voice.synthesize_wav(text, output, syn_config=SynthesisConfig(length_scale=1.05))
                with wave.open(str(wav_path), 'rb') as source:
                    duration = source.getnframes() / source.getframerate()
                filename = f'{identifier}.m4a'
                subprocess.run(['afconvert', '-f', 'm4af', '-d', 'aac', '-b', '64000', str(wav_path), str(output_dir / filename)], check=True)
                manifest['clips'][identifier] = {
                    'path': f'polskiflow/audio/practice/{filename}',
                    'transcript_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                    'sha256': hashlib.sha256((output_dir / filename).read_bytes()).hexdigest(),
                    'duration_seconds': duration,
                }
                print(f'{identifier} generated')
    (root / 'domain/practice_listening_media.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
