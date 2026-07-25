"""
shared and privacy-preserving rate limiting.

Fixed window token bucket backed by the dedicated 'ratelimit' file cache.
'allow' function checks: 1. small per-client cap 2. larger global ceiling bounding
distributed flood. Checking the client cap first means a blocked source never
spends the shared global budget.

The per-client key is an HMAC of the caller's IP (IPv6 collapsed to its /64),
never the raw address. Only an opaque counter that expires with the window is
ever written, so no IP is stored, logged, or otherwise persisted here.
"""
import hashlib
import hmac
import ipaddress
import time

from django.conf import settings
from django.core.cache import caches


def _bump_counter(key: str, ttl: int) -> int:
    """increment a window counter and return the new value

    Not atomic across workers, but concurrent increments only ever under-count,
    which fails open in the callers favour rather than wrongly blocking.
    """
    cache = caches['ratelimit']
    cache.add(key, 0, ttl)
    try:
        return cache.incr(key)
    except ValueError:
        # entry expired between the add and the incr, restart the window.
        cache.set(key, 1, ttl)
        return 1


def consume_token_bucket(key: str, limit: int, window_seconds: int = 3600) -> bool:
    """Fixed-window limit. True while the caller is under the cap.

    The window index is baked into the key, so correctness never depends on the
    cache honouring a TTL: a rolled bucket is never read again and is reaped by
    the purge_expired cache sweep.
    """
    if limit <= 0:
        return True
    bucket = int(time.time()) // window_seconds
    return _bump_counter(f'{key}:{bucket}', window_seconds * 2) <= limit


def _client_ip(request) -> str:
    header = getattr(settings, 'RATELIMIT_IP_HEADER', None)
    if header:
        # trusted-proxy header only. Take first hop aka client
        return (request.META.get(header, '') or '').split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or ''


def _client_group(ip: str) -> str:
    """Collapse address to its rate-limit group: full IPv4, /64 for IPv6."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return ip or 'unknown'
    if addr.version == 6:
        net = ipaddress.ip_network(f'{addr}/64', strict=False)
        return str(net.network_address)
    return str(addr)


def client_key(request) -> str:
    """Opaque per-client token, HMAC(SECRET_KEY, ip group). No raw IP kept."""
    group = _client_group(_client_ip(request)).encode()
    return hmac.new(settings.SECRET_KEY.encode(), group,
                    hashlib.sha256).hexdigest()[:16]


def allow(request, name: str, *, per_ip: int = None,
          global_: int = None, window: int = 3600) -> bool:
    """Layered check: per-client cap first, then the global ceiling."""
    if per_ip and not consume_token_bucket(
            f'rl:{name}:ip:{client_key(request)}', per_ip, window):
        return False
    if global_ and not consume_token_bucket(f'rl:{name}:all', global_, window):
        return False
    return True
