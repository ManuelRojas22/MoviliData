from django.test import SimpleTestCase
from .services import risk_zone_layer


class MapTests(SimpleTestCase):
    def test_layer(self):
        self.assertTrue(risk_zone_layer())
