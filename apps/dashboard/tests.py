from django.test import SimpleTestCase
from .services import city_summary


class DashboardServicesTests(SimpleTestCase):
    def test_city_summary_has_metrics(self):
        self.assertGreater(len(city_summary()["metrics"]), 0)
