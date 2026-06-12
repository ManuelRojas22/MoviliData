from django.test import SimpleTestCase
from .services import recommended_routes


class RouteTests(SimpleTestCase):
    def test_routes_sorted(self):
        routes = recommended_routes()
        self.assertLessEqual(routes[0]["risk"], routes[-1]["risk"])
