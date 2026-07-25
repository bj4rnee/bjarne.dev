from django.core.cache import cache, caches
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import VisitCounter


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
