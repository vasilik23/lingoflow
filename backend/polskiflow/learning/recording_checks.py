"""Release checks for B1 audio assets and their provenance."""

from datetime import date
from hashlib import sha256
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from django.contrib.staticfiles import finders
from django.core.checks import Error, register

from polskiflow.domain import b1_listening_recordings as recordings
from polskiflow.domain.b1_weekly_mock import get_mock_variant


@register()
def check_b1_recordings(app_configs, **kwargs):
    errors = []
    ids, paths = set(), set()
    for item in recordings.RECORDINGS:
        problems = []
        if item.id in ids or item.static_path in paths:
            problems.append("duplicate recording ID or path")
        ids.add(item.id)
        paths.add(item.static_path)
        if any(not getattr(item, field).strip() for field in item.__dataclass_fields__):
            problems.append("missing provenance or review metadata")
        if item.license not in {"CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "CC-BY-SA-3.0", "LicenseRef-Public-Domain", "LicenseRef-PolskiFlow-Permission"}:
            problems.append("unapproved license")
        for url in (item.source_url, item.license_url):
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                problems.append("source and license must use public HTTPS URLs")
        try:
            date.fromisoformat(item.verified_at)
        except ValueError:
            problems.append("invalid review date")
        variant = get_mock_variant(item.variant_id)
        if not variant or item.transcript_sha256 != recordings.transcript_checksum(variant.listening_transcript):
            problems.append("recording transcript does not match the variant")
        path = PurePosixPath(item.static_path)
        safe_path = item.static_path.startswith("polskiflow/audio/b1/") and ".." not in path.parts and path.suffix.lower() in {".mp3", ".ogg", ".wav"} and "\\" not in item.static_path
        found = finders.find(item.static_path) if safe_path else None
        if not found or not Path(found).is_file():
            problems.append("missing local audio file or unsafe static path")
        elif sha256(Path(found).read_bytes()).hexdigest() != item.sha256:
            problems.append("audio checksum mismatch")
        if problems:
            errors.append(Error(f"B1 recording {item.id}: {'; '.join(problems)}", id="learning.E001"))
    return errors
