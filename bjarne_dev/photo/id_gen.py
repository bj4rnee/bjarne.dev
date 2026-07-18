"""
Photo ID generation.

5 random alnum chars. On collision-pressure escalation, grows to 8. The id
is the stem of the derivative filenames on disk.
"""
import secrets
import string

from .models import Photograph

ALPHABET = string.ascii_letters + string.digits
MAX_ATTEMPTS_PER_LENGTH = 250
MIN_LENGTH = 5
MAX_LENGTH = 8


def generate_photo_id() -> str:
    length = MIN_LENGTH
    while length <= MAX_LENGTH:
        for _ in range(MAX_ATTEMPTS_PER_LENGTH):
            candidate = ''.join(secrets.choice(ALPHABET) for _ in range(length))
            if not Photograph.objects.filter(photo_id=candidate).exists():
                return candidate
        length += 1
    raise RuntimeError('Unable to generate unique photo_id after maximum attempts')
