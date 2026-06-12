from django.test import SimpleTestCase
from .services import traffic_snapshot


class TrafficTests(SimpleTestCase):
    def test_snapshot(self):
        self.assertTrue(traffic_snapshot())
