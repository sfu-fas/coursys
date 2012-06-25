from django.test import TestCase
from django.test.client import Client
from settings import CAS_SERVER_URL
from django.core.urlresolvers import reverse
import json

class PlanningTest(TestCase):
    
    def test_that_planning_admin_returns_200_ok(self):
        """
        Tests basic page permissions
        """
        client = Client()
        client.login(ticket="dixon", service=CAS_SERVER_URL)
        response = client.get(reverse('planning.views.admin_index'))
        self.assertEqual(response.status_code, 200)

    def test_that_planning_admin_returns_403_forbidden(self):
        """
        Tests basic page authentication for instructor
        """
        client = Client()
        client.login(ticket="ggbaker", service=CAS_SERVER_URL)
        response = client.get(reverse('planning.views.admin_index'))
        self.assertEqual(response.status_code, 403)