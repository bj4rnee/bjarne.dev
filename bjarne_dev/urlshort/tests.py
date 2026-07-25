from django.core.cache import caches
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Shorted_url


@override_settings(URLSHORT_CREATE_IP_RATE=2, URLSHORT_CREATE_RATE=1000)
class UrlshortRateLimitTests(TestCase):
    def setUp(self):
        caches['ratelimit'].clear()

    def _shorten(self, url):
        return self.client.get(reverse('urlshort'), {'url': url, 'json': '1'})

    def test_creates_under_cap(self):
        resp = self._shorten('https://example.com/a')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()['error'])
        self.assertTrue(
            Shorted_url.objects.filter(original_url='https://example.com/a').exists())

    def test_blocks_over_per_ip_cap(self):
        self.assertEqual(self._shorten('https://example.com/1').status_code, 200)
        self.assertEqual(self._shorten('https://example.com/2').status_code, 200)
        blocked = self._shorten('https://example.com/3')
        self.assertEqual(blocked.status_code, 429)
        self.assertTrue(blocked.json()['error'])
        # the blocked request must not have created a row
        self.assertFalse(
            Shorted_url.objects.filter(original_url='https://example.com/3').exists())

    @override_settings(URLSHORT_CREATE_IP_RATE=1000, URLSHORT_CREATE_RATE=1)
    def test_global_ceiling_blocks_across_the_cap(self):
        self.assertEqual(self._shorten('https://example.com/x').status_code, 200)
        self.assertEqual(self._shorten('https://example.com/y').status_code, 429)
