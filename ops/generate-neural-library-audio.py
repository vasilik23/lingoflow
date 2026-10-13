"""Offline reading/B1 audio generation; no production TTS dependencies."""
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
from concurrent.futures import ThreadPoolExecutor
from threading import Lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('transcripts', type=Path)
    parser.add_argument('model', type=Path)
    parser.add_argument('--runtime-dir', type=Path)
    parser.add_argument('--resume-manifest', type=Path)
    parser.add_argument('--progress-manifest', type=Path)
    args = parser.parse_args()
    if args.runtime_dir:
        sys.path.insert(0, str(args.runtime_dir))
    from piper import PiperVoice, SynthesisConfig
    import onnxruntime
    inputs = json.loads(args.transcripts.read_text(encoding='utf-8'))
    import re
    if not inputs or any(not re.fullmatch(r'(reading|b1)-[\w-]+', key) or
                         not isinstance(value, str) or not value.strip()
                         for key, value in inputs.items()):
        parser.error('Expected reading-/b1- identifiers and nonempty Polish texts')
    root = Path(__file__).resolve().parents[1] / 'backend/polskiflow'
    model_hash = hashlib.sha256(args.model.read_bytes()).hexdigest()
    approved = json.loads((root / 'domain/practice_listening_media.json').read_text())
    if model_hash != approved['model_sha256']:
        parser.error('Model does not match the approved stock voice checksum')
    voice = PiperVoice.load(str(args.model))
    options = onnxruntime.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    voice.session = onnxruntime.InferenceSession(str(args.model), sess_options=options, providers=['CPUExecutionProvider'])
    output_dir = root / 'learning/static/polskiflow/audio/library'
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        'engine': f'Piper {importlib.metadata.version("piper-tts")}',
        'voice': 'pl_PL-bass-high', 'model_source': 'https://huggingface.co/blackbartblues/piper-pl-bass-high',
        'model_revision': 'd38fb15ed4eec60c124e3da1fd67359af771c3dc',
        'model_license': 'Apache-2.0 (publisher declaration)',
        'model_sha256': model_hash,
        'config_sha256': hashlib.sha256(Path(str(args.model) + '.json').read_bytes()).hexdigest(),
        'synthesis': {'length_scale': 1.05, 'codec': 'AAC', 'bitrate': 64000},
        'created_at': date.today().isoformat(), 'origin': 'original', 'created_for': 'LingoFlow',
        'verification': 'exact transcript input; independent pronunciation review pending',
        'clips': {},
    }
    previous = {}
    if args.resume_manifest:
        resume = json.loads(args.resume_manifest.read_text())
        if resume.get('model_sha256') != model_hash:
            parser.error('Resume manifest uses a different or unidentified model')
        if resume.get('config_sha256') != manifest['config_sha256'] or resume.get('synthesis') != manifest['synthesis']:
            parser.error('Resume manifest uses different synthesis settings')
        previous = resume['clips']
    lock = Lock()
    def store_clip(identifier, clip):
        with lock:
            manifest['clips'][identifier] = clip
            if args.progress_manifest:
                temporary = args.progress_manifest.with_suffix('.tmp')
                temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                temporary.replace(args.progress_manifest)
    with tempfile.TemporaryDirectory(prefix='lingoflow-neural-audio-') as workdir:
        def generate(item):
            name, transcript = item
            texts = {'full': transcript}
            for part, text in texts.items():
                identifier = f'{name}-{part}'
                old = previous.get(identifier)
                if old and old['transcript_sha256'] == hashlib.sha256(text.encode('utf-8')).hexdigest():
                    existing = root / 'learning/static' / old['path']
                    if existing.is_file() and hashlib.sha256(existing.read_bytes()).hexdigest() == old['sha256']:
                        store_clip(identifier, old)
                        print(f'{identifier} reused', flush=True)
                        continue
                wav_path = Path(workdir) / f'{identifier}.wav'
                with wave.open(str(wav_path), 'wb') as output:
                    voice.synthesize_wav(text, output, syn_config=SynthesisConfig(length_scale=1.05))
                with wave.open(str(wav_path), 'rb') as source:
                    duration = source.getnframes() / source.getframerate()
                filename = f'{identifier}.m4a'
                subprocess.run(['afconvert', '-f', 'm4af', '-d', 'aac', '-b', '64000', str(wav_path), str(output_dir / filename)], check=True)
                store_clip(identifier, {
                    'path': f'polskiflow/audio/library/{filename}',
                    'transcript_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                    'sha256': hashlib.sha256((output_dir / filename).read_bytes()).hexdigest(),
                    'duration_seconds': duration,
                })
                print(f'{identifier} generated', flush=True)
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(generate, inputs.items()))
    manifest['clips'] = dict(sorted(manifest['clips'].items()))
    (root / 'domain/library_audio.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
