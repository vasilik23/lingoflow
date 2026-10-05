"""A shared, deterministic version for the public PWA shell."""

import hashlib
import os
from pathlib import Path


def build_shell_version(release_id: str, assets: tuple[bytes, ...] = ()) -> str:
    digest = hashlib.sha256()
    if release_id:
        digest.update(b"release\0" + release_id.encode())
    else:
        for asset in assets:
            digest.update(len(asset).to_bytes(8, "big"))
            digest.update(asset)
    return "build-" + digest.hexdigest()[:16]


def current_shell_version() -> str:
    release_id = os.environ.get("VERCEL_GIT_COMMIT_SHA") or os.environ.get("VERCEL_DEPLOYMENT_ID", "")
    if release_id:
        return build_shell_version(release_id)
    backend = Path(__file__).resolve().parent.parent
    assets = (
        "templates/base.html", "templates/offline.html", "polskiflow/pwa_views.py",
        "polskiflow/learning/static/polskiflow/app.css",
        "polskiflow/learning/static/polskiflow/favicon.svg",
    )
    return build_shell_version("", tuple((backend / path).read_bytes() for path in assets))


PWA_SHELL_VERSION = current_shell_version()


def pwa_shell_context(_request):
    return {"pwa_shell_version": PWA_SHELL_VERSION}
