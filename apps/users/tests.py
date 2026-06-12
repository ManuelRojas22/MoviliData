from django.test import SimpleTestCase
from .services import demo_credentials


class UserTests(SimpleTestCase):
    def test_demo_user(self):
        self.assertEqual(demo_credentials()["username"], "admin")
