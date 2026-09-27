import time
from unittest import mock

from django.conf import settings
from django.core.cache import cache, caches
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import VisitCounter

# ipaddress counts documentation ranges as private, reverse DNS tests need addresses that are globally routable
GLOBAL_V4 = '93.184.216.34'
GLOBAL_V4_OTHER = '9.9.9.9'
GLOBAL_V6 = '2a02:8106:286:f200:dd47:5c52:b8b5:457f'


@override_settings(INDEX_VISIT_IP_RATE=2, INDEX_VISIT_RATE=1000)
class VisitCounterRateLimitTests(TestCase):
    def setUp(self):
        caches['ratelimit'].clear()
        cache.clear()

    def _spend(self, token):
        # mint a token the way index_view would, then have the client spend it
        cache.set(f'visit-token:{token}', 1, 300)
        return self.client.get(reverse('track_visit'), {'token': token})

    def test_counts_under_cap(self):
        self.assertEqual(self._spend('t1').status_code, 200)
        self.assertEqual(VisitCounter.objects.get(pk=1).count, 1)

    def test_blocks_over_per_ip_cap(self):
        self.assertEqual(self._spend('a').status_code, 200)
        self.assertEqual(self._spend('b').status_code, 200)
        blocked = self._spend('c')
        self.assertEqual(blocked.status_code, 429)
        # the third visit was rejected, so the counter stops at two
        self.assertEqual(VisitCounter.objects.get(pk=1).count, 2)

    def test_invalid_token_does_not_spend_budget(self):
        # invalid tokens never reach the limiter, so they cannot exhaust it
        for _ in range(5):
            r = self.client.get(reverse('track_visit'), {'token': 'nope'})
            self.assertEqual(r.status_code, 400)
        self.assertEqual(self._spend('ok').status_code, 200)
        self.assertEqual(VisitCounter.objects.get(pk=1).count, 1)


class IpPageTests(TestCase):
    def setUp(self):
        caches['ratelimit'].clear()
        cache.clear()

    def _json(self, params=None, **extra):
        return self.client.get(reverse('ip'), params or {'json': '1'}, **extra).json()

    def test_page_renders_and_is_never_cached(self):
        resp = self.client.get(reverse('ip'))
        self.assertEqual(resp.status_code, 200)
        # Webserver must not hand one visitor a copy built for another
        self.assertIn('no-store', resp['Cache-Control'])
        self.assertContains(resp, '127.0.0.1')

    def test_json_payload_shape(self):
        data = self._json()
        self.assertEqual(set(data),
                         {'client', 'request', 'server', 'cookies', 'headers'})
        self.assertEqual(data['client']['family'], 'IPv4')
        self.assertEqual(data['client']['scope'], 'loopback')
        # page never blocks on resolver
        self.assertIsNone(data['client']['reverse_dns'])

    def test_ipv6_peer_is_grouped_by_64(self):
        data = self._json(REMOTE_ADDR=GLOBAL_V6)
        self.assertEqual(data['client']['family'], 'IPv6')
        self.assertEqual(data['client']['scope'], 'global')
        self.assertEqual(data['client']['v6_group'], '2a02:8106:286:f200::/64')

    def test_address_forms_are_classified(self):
        cases = {
            '100.64.0.1': 'CGNAT',
            '10.0.0.4': 'private',
            'fd00::1': 'unique-local',
            'fe80::1': 'link-local',
            '::1': 'loopback',
            GLOBAL_V4: 'global',
        }
        for address, scope in cases.items():
            with self.subTest(address=address):
                self.assertEqual(self._json(REMOTE_ADDR=address)['client']['scope'], scope)

    def test_mapped_peer_is_reported_as_the_v4_it_is(self):
        data = self._json(REMOTE_ADDR=f'::ffff:{GLOBAL_V4}')
        self.assertEqual(data['client']['family'], 'IPv4 in IPv6 form')
        self.assertEqual(data['client']['scope'], 'global')
        self.assertIn('4-in-6 mapped', data['client']['v6_kind'])

    def test_unparseable_peer_address_is_reported_not_raised(self):
        data = self._json(REMOTE_ADDR='')
        self.assertIsNone(data['client']['ip'])
        self.assertIsNone(data['client']['family'])
        self.assertIsNone(data['client']['scope'])

    def test_session_secrets_are_never_echoed(self):
        self.client.cookies['sessionid'] = 'averysecretsessionvalue'
        resp = self.client.get(reverse('ip'), {'json': '1'},
                               HTTP_AUTHORIZATION='Bearer supersecrettoken')
        body = resp.content.decode()
        self.assertNotIn('averysecretsessionvalue', body)
        self.assertNotIn('supersecrettoken', body)

        data = resp.json()
        self.assertEqual(data['cookies']['sessionid'], '23 chars')
        self.assertIn('redacted', data['headers']['Authorization'])
        self.assertIn('redacted', data['headers']['Cookie'])

    def test_server_environment_never_reaches_the_page(self):
        # extra kwargs land in request.META the way the process env does under wsgi
        resp = self.client.get(reverse('ip'), {'json': '1'},
                               HTTP_X_DEBUG_MARKER='visible',
                               DJANGO_SECRET_KEY='must-not-leak')
        data = resp.json()
        self.assertEqual(data['headers']['X-Debug-Marker'], 'visible')
        self.assertNotIn('DJANGO_SECRET_KEY', data['headers'])
        body = resp.content.decode()
        self.assertNotIn('must-not-leak', body)
        self.assertNotIn(settings.SECRET_KEY, body)

    def test_ping_is_an_empty_204(self):
        resp = self.client.get(reverse('ip_ping'))
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(resp.content, b'')
        self.assertIn('no-store', resp['Cache-Control'])


class IpReverseDnsTests(TestCase):
    def setUp(self):
        caches['ratelimit'].clear()
        cache.clear()

    def _rdns(self, **extra):
        return self.client.get(reverse('ip_rdns'), **extra).json()['reverse_dns']

    def test_addresses_without_a_possible_ptr_are_skipped(self):
        with mock.patch('index.views.socket.gethostbyaddr') as resolver:
            for address in ('127.0.0.1', '10.0.0.4', '100.64.0.1'):
                self.assertIn('not globally routable', self._rdns(REMOTE_ADDR=address))
        resolver.assert_not_called()

    def test_lookup_resolves_once_and_is_then_cached(self):
        with mock.patch('index.views.socket.gethostbyaddr',
                        return_value=('host.example.net', [], [GLOBAL_V4])) as resolver:
            first = self._rdns(REMOTE_ADDR=GLOBAL_V4)
            second = self._rdns(REMOTE_ADDR=GLOBAL_V4)
        self.assertEqual(first, 'host.example.net')
        self.assertEqual(second, 'host.example.net')
        self.assertEqual(resolver.call_count, 1)

    def test_absent_ptr_record_is_stated(self):
        with mock.patch('index.views.socket.gethostbyaddr', side_effect=OSError):
            self.assertEqual(self._rdns(REMOTE_ADDR=GLOBAL_V4), 'no PTR record')

    def test_slow_resolver_does_not_hold_the_request(self):
        def stall(_):
            time.sleep(0.4)
            return ('too.late', [], [])

        with mock.patch('index.views.RDNS_TIMEOUT', 0.05), \
                mock.patch('index.views.socket.gethostbyaddr', side_effect=stall):
            started = time.monotonic()
            answer = self._rdns(REMOTE_ADDR=GLOBAL_V4)
            elapsed = time.monotonic() - started
        self.assertIn('timed out', answer)
        self.assertLess(elapsed, 0.3)

    @override_settings(IP_RDNS_RATE=1)
    def test_only_real_lookups_spend_the_cap(self):
        with mock.patch('index.views.socket.gethostbyaddr',
                        return_value=('a.example.net', [], [])) as resolver:
            self.assertEqual(self._rdns(REMOTE_ADDR=GLOBAL_V4), 'a.example.net')
            # cached, reload costs no budget
            self.assertEqual(self._rdns(REMOTE_ADDR=GLOBAL_V4), 'a.example.net')
            # different address needs the resolver and the cap is spent
            self.assertIn('rate limit', self._rdns(REMOTE_ADDR=GLOBAL_V4_OTHER))
        self.assertEqual(resolver.call_count, 1)

    def test_page_resolves_on_request(self):
        with mock.patch('index.views.socket.gethostbyaddr',
                        return_value=('host.example.net', [], [])):
            data = self.client.get(reverse('ip'), {'json': '1', 'rdns': '1'},
                                   REMOTE_ADDR=GLOBAL_V4).json()
        self.assertEqual(data['client']['reverse_dns'], 'host.example.net')
