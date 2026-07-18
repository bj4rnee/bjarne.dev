"""
On-disk layout for generated photo derivatives.

Each photo yields two AVIF files named '<photo_id>_thumb.avif' and
'<photo_id>_large.avif'. In production the storage dir sits inside 'public_html/static',
so image bytes never pass back through Python. In DEBUG it lives under MEDIA_ROOT.
"""
import os
from pathlib import Path

from django.conf import settings

KINDS = ('thumb', 'large')


def storage_root() -> Path:
    root = Path(settings.PHOTO_STORAGE_DIR)
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(root, 0o755)  # compensate for umask, must stay web-readable
        except OSError:
            pass
    return root


def derivative_name(photo_id: str, kind: str) -> str:
    return f'{photo_id}_{kind}.avif'


def derivative_path(photo_id: str, kind: str) -> Path:
    return storage_root() / derivative_name(photo_id, kind)


def derivative_url(photo_id: str, kind: str) -> str:
    base = settings.PHOTO_STORAGE_URL
    if not base.endswith('/'):
        base += '/'
    return f'{base}{derivative_name(photo_id, kind)}'


def unlink_derivatives(photo_id: str) -> None:
    for kind in KINDS:
        try:
            derivative_path(photo_id, kind).unlink()
        except OSError:
            pass
