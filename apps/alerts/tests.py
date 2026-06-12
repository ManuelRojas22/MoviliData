from django.test import SimpleTestCase
from .services import active_alerts


class AlertTests(SimpleTestCase):
    def test_alerts(self):
        self.assertTrue(active_alerts())
