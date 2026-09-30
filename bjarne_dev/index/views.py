from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.core.cache import cache
from django.http.request import split_domain_port
from django.utils import timezone
from datetime import datetime, timedelta, date, timezone as dt_timezone
import ipaddress
import platform
import secrets
import socket
import ssl
import threading
import django
from bjarne_dev import ratelimit
from .models import VisitCounter
from django.db.models import F


def index_view(request):
    # unique token for this visit
    token = secrets.token_urlsafe(16)
    key = f'visit-token:{token}'
    cache.set(key, 1, timeout=300)  # 5-minute TTL
    # get total visits from DB (no create if not exists)
    try:
        total_visits = VisitCounter.objects.get(pk=1).count
    except VisitCounter.DoesNotExist:
        total_visits = 0
    context = {
        'time': datetime.now().strftime('%H:%M:%S'),
        'visit_token': token,
        'total_visits': str(total_visits + 1).zfill(5),
    }
    return render(request, "index.html", context)

def track_visit(request):
    token = request.GET.get('token')
    key = f'visit-token:{token}'
    if cache.get(key):
        # only "real" page loads should reach here, so this bounds counter inflation
        if not ratelimit.allow(request, 'idx:visit',
                               per_ip=settings.INDEX_VISIT_IP_RATE,
                               global_=settings.INDEX_VISIT_RATE):
            return JsonResponse({'status': 'rate_limited'}, status=429)
        # atomic increment in DB
        updated = VisitCounter.objects.filter(pk=1).update(count=F('count') + 1)
        if updated == 0:
            # create with count=1 if it didnt exist
            VisitCounter.objects.create(pk=1, count=1)
        cache.delete(key)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'invalid'}, status=400)

# ---------------------------------------------------------------------------
# /ip/ connection debug page
# ---------------------------------------------------------------------------
# Headers from request.headers (HTTP_* only). request.META carries process environment

CGNAT_V4 = ipaddress.ip_network('100.64.0.0/10')
ULA_V6 = ipaddress.ip_network('fc00::/7')

# JSON should not leak live session
REDACTED_HEADERS = {'cookie', 'authorization', 'proxy-authorization'}

RDNS_TIMEOUT = 1.5  # seconds a PTR lookup may hold worker
RDNS_TTL = 600      # cache for resolved name or a confirmed absence
RDNS_FAIL_TTL = 60  # cache timeout briefly: cheap reload

CERT_TIMEOUT = 2
CERT_TTL = 3600     # hour is plenty
CERT_FAIL_TTL = 300

_MISS = object()


def _address_facts(raw):
    """Classify the peer address"""
    facts = {'ip': raw or None, 'family': None, 'scope': None,
             'v6_kind': None, 'v6_group': None}
    try:
        addr = ipaddress.ip_address(raw)
    except ValueError:
        return facts

    facts['family'] = f'IPv{addr.version}'
    tunnelled = False
    if addr.version == 6:
        if addr.ipv4_mapped:
            # plain IPv4 peer on a dual-stack socket, classify the v4
            facts['v6_kind'] = f'4-in-6 mapped, {addr.ipv4_mapped}'
            facts['family'] = 'IPv4 in IPv6 form'
            addr = addr.ipv4_mapped
        else:
            if addr.teredo:
                facts['v6_kind'] = f'teredo, client v4 {addr.teredo[1]}'
                tunnelled = True
            elif addr.sixtofour:
                facts['v6_kind'] = f'6to4, client v4 {addr.sixtofour}'
                tunnelled = True
            # same /64 grouping rate limiter buckets by
            net = ipaddress.ip_network(f'{addr}/64', strict=False)
            facts['v6_group'] = f'{net.network_address}/64'

    if addr.is_loopback:
        facts['scope'] = 'loopback'
    elif addr.is_link_local:
        facts['scope'] = 'link-local'
    elif tunnelled:
        # private according to ipaddress, but they carry a global v4
        facts['scope'] = 'tunnelled'
    elif addr.version == 4 and addr in CGNAT_V4:
        facts['scope'] = 'CGNAT'
    elif addr.version == 6 and addr in ULA_V6:
        facts['scope'] = 'unique-local'
    elif addr.is_private:
        facts['scope'] = 'private'
    elif addr.is_global:
        facts['scope'] = 'global'
    else:
        facts['scope'] = 'reserved'
    return facts


def _rdns_lookup(ip):
    """PTR for one address. '' is no record and None is a timeout"""
    box = {}

    def resolve():
        try:
            box['name'] = socket.gethostbyaddr(ip)[0]
        except OSError:
            box['name'] = ''

    worker = threading.Thread(target=resolve, daemon=True)
    worker.start()
    # socket timeout dont reach libc, a black-holed PTR zone stalls this
    # thread past the join. finishes on its own. request does not wait
    worker.join(RDNS_TIMEOUT)
    return box.get('name')


def _rdns_result(request, client):
    """reverse_dns row, only ever the caller's own address"""
    if client['scope'] != 'global':
        return 'skipped, not globally routable'

    key = f'ip-rdns:{client["ip"]}'
    name = cache.get(key, _MISS)
    if name is _MISS:
        # a cached answer is free, real resolver traffic spends budget
        if not ratelimit.allow(request, 'idx:rdns',
                               per_ip=settings.IP_RDNS_IP_RATE,
                               global_=settings.IP_RDNS_RATE):
            return 'skipped, rate limit reached'
        name = _rdns_lookup(client['ip'])
        cache.set(key, name, RDNS_TTL if name is not None else RDNS_FAIL_TTL)

    if name is None:
        return f'timed out after {RDNS_TIMEOUT:g}s'
    return name or 'no PTR record'


def _cert_lookup(host):
    ctx = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=CERT_TIMEOUT) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as tls:
            cert = tls.getpeercert()
    return [datetime.fromtimestamp(ssl.cert_time_to_seconds(cert[k]), dt_timezone.utc).isoformat()
            for k in ('notBefore', 'notAfter')]


def _cert_dates(request):
    """issued/expires of own cert"""
    # tls ends in webserver. hacky fix is to connect to self like client would
    if not request.is_secure():
        return None, None
    host = split_domain_port(request.get_host())[0]
    key = f'ip-cert:{host}'
    dates = cache.get(key)
    if dates is None:
        try:
            dates = _cert_lookup(host)
            cache.set(key, dates, CERT_TTL)
        except (OSError, ValueError, KeyError):
            dates = ['lookup failed'] * 2
            cache.set(key, dates, CERT_FAIL_TTL)
    return dates


def _request_headers(request):
    out = {}
    for name, value in sorted(request.headers.items()):
        if name.lower() in REDACTED_HEADERS:
            out[name] = f'[redacted, {len(value)} chars]'
        else:
            out[name] = value
    return out


def _ip_payload(request):
    now = timezone.now()
    client = _address_facts(request.META.get('REMOTE_ADDR', ''))
    client['source_port'] = request.META.get('REMOTE_PORT') or None
    # set by webserver, overwrites what client sent
    client['forwarded_for'] = request.headers.get('X-Forwarded-For')
    client['reverse_dns'] = None
    cert_issued, cert_expires = _cert_dates(request)

    return {
        'client': client,
        'request': {
            'method': request.method,
            'path': request.get_full_path(),
            'host': request.get_host(),
            'scheme': request.scheme,
            'secure': request.is_secure(),
            # LSAPI may report 1.1 even when browser negotiated h2
            'server_protocol': request.META.get('SERVER_PROTOCOL'),
            'time_utc': now.isoformat(timespec='seconds'),
            'time_local': timezone.localtime(now).isoformat(timespec='seconds'),
            'epoch_ms': int(now.timestamp() * 1000),
        },
        'server': {
            'software': request.META.get('SERVER_SOFTWARE'),
            'python': platform.python_version(),
            'django': django.get_version(),
            'time_zone': settings.TIME_ZONE,
            'debug': settings.DEBUG,
            'cert_issued': cert_issued,
            'cert_expires': cert_expires,
        },
        'cookies': {name: f'{len(value)} chars'
                    for name, value in sorted(request.COOKIES.items())},
        'headers': _request_headers(request),
    }


def _text(value):
    if value is None:
        return 'n/a'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


def _cls(value):
    # bool coloring
    if value is True:
        return 'ip_yes'
    if value is False:
        return 'ip_no'
    return ''


def _rows(payload, *names):
    return [(name, [(key, _text(value), _cls(value)) for key, value in payload[name].items()])
            for name in names]


def _no_store(response):
    # cached copy would show one visitor anothers connection BAD :(
    response['Cache-Control'] = 'no-store, max-age=0'
    return response


def ip_view(request):
    payload = _ip_payload(request)
    if request.GET.get('rdns'):
        payload['client']['reverse_dns'] = _rdns_result(request, payload['client'])

    if request.GET.get('json'):
        return _no_store(JsonResponse(payload))

    context = {
        'payload': payload,
        'client_ip': payload['client']['ip'] or 'unknown',
        'sections': _rows(payload, 'client', 'request', 'server'),
        'dump': _rows(payload, 'cookies', 'headers'),
    }
    return _no_store(render(request, 'ip.html', context))


def ip_ping(request):
    """Empty 204, target for client-side RTT sampling"""
    return _no_store(HttpResponse(status=204))


def ip_rdns(request):
    """PTR on its own route, page never blocks on DNS"""
    client = _address_facts(request.META.get('REMOTE_ADDR', ''))
    return _no_store(JsonResponse({'reverse_dns': _rdns_result(request, client)}))


# display-debug static page
def display_view(request):
    return render(request, 'display.html')


# custom csrf failure view to use 403.html
def csrf_failure(request, reason=""):
    return render(request, "403.html", {"reason": reason}, status=403)
