"""
Pillow ingest for uploaded photographs.

One upload becomes two AVIF derivatives: a grid thumbnail and a larger view
image for the lightbox. The original is never kept,
so we downscale to sane web dimensions on ingest.

EXIF is read first for metadata pre-fill, then dropped from the derivatives
so no GPS location or camera serial leaks. Orientation is baked
into the pixels via exif_transpose so the stripped output still displays the
right way up.
"""
from datetime import datetime

from django.conf import settings
from django.utils import timezone
from PIL import Image, ImageOps, ExifTags

from . import storage

# pointer tag to the Exif sub-IFD, where the capture-time and exposure tags
# live. Using the raw id hopefully keeps this working across Pillow versions
EXIF_OFFSET = 0x8769

RESAMPLE = Image.Resampling.LANCZOS


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _format_aperture(value) -> str:
    f = _to_float(value)
    return f'f/{f:g}' if f else ''


def _format_shutter(value) -> str:
    f = _to_float(value)
    if not f:
        return ''
    if f >= 1:
        return f'{f:g}s'
    return f'1/{round(1 / f)}'


def _format_focal(value) -> str:
    f = _to_float(value)
    return f'{round(f)}mm' if f else ''


def _format_camera(make, model) -> str:
    make = (make or '').strip()
    model = (model or '').strip()
    if not model:
        return make
    # model often already carries the brand, avoid dupes
    if make and not model.lower().startswith(make.lower().split(' ')[0]):
        return f'{make} {model}'
    return model


def _parse_capture_date(value):
    if isinstance(value, bytes):
        value = value.decode('ascii', 'ignore')
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.strptime(value.strip(), '%Y:%m:%d %H:%M:%S')
    except ValueError:
        return None
    try:
        return timezone.make_aware(dt, timezone.get_current_timezone())
    except Exception:
        return dt


def _extract_metadata(pil_img) -> dict:
    exif = pil_img.getexif()
    if not exif:
        return {}
    base = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
    try:
        sub = {ExifTags.TAGS.get(k, k): v for k, v in exif.get_ifd(EXIF_OFFSET).items()}
    except Exception:
        sub = {}

    iso = sub.get('ISOSpeedRatings') or sub.get('PhotographicSensitivity')
    if isinstance(iso, (list, tuple)):
        iso = iso[0] if iso else None
    try:
        iso = int(iso) if iso is not None else None
    except (TypeError, ValueError):
        iso = None

    lens = sub.get('LensModel')
    return {
        'camera': _format_camera(base.get('Make'), base.get('Model')),
        'lens': lens.strip() if isinstance(lens, str) else '',
        'focal_length': _format_focal(sub.get('FocalLength')),
        'aperture': _format_aperture(sub.get('FNumber')),
        'shutter_speed': _format_shutter(sub.get('ExposureTime')),
        'iso': iso,
        'capture_date': _parse_capture_date(
            sub.get('DateTimeOriginal') or base.get('DateTime')
        ),
    }


def _orientation(width: int, height: int) -> str:
    if width > height:
        return 'landscape'
    if height > width:
        return 'portrait'
    return 'square'


def process_upload(fileobj, photo_id: str, speed=None) -> dict:
    """Read EXIF, write both AVIF derivatives, return dims + metadata.

    'fileobj' is any file-like the caller owns (a Django UploadedFile in
    admin). 'speed' overrides PHOTO_AVIF_SPEED for this encode. Returns
    width/height of the large image, its orientation, and a metadata dict
    for blank-field pre-fill.
    """
    fileobj.seek(0)
    with Image.open(fileobj) as img:
        img.load()
        metadata = _extract_metadata(img)
        img = ImageOps.exif_transpose(img)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        large = img.copy()
        large.thumbnail(
            (settings.PHOTO_LARGE_EDGE, settings.PHOTO_LARGE_EDGE), RESAMPLE)
        thumb = img.copy()
        thumb.thumbnail(
            (settings.PHOTO_THUMB_EDGE, settings.PHOTO_THUMB_EDGE), RESAMPLE)

    quality = settings.PHOTO_AVIF_QUALITY
    if speed is None:
        speed = settings.PHOTO_AVIF_SPEED
    storage.storage_root()
    large.save(storage.derivative_path(photo_id, 'large'),
               'AVIF', quality=quality, speed=speed)
    thumb.save(storage.derivative_path(photo_id, 'thumb'),
               'AVIF', quality=quality, speed=speed)

    width, height = large.size
    return {
        'width': width,
        'height': height,
        'orientation': _orientation(width, height),
        'metadata': metadata,
    }
