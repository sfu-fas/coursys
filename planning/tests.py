from django.test import TestCase
from django.test.client import Client
from settings import CAS_SERVER_URL
from django.core.urlresolvers import reverse
import json

class PlanningTest(TestCase):
    fixtures = ['test_data']
    
    def test_that_planning_admin_returns_200_ok(self):
        """
        Tests basic page permissions
        """
        client = Client()
        client.login(ticket="dixon", service=CAS_SERVER_URL)
        response = client.get(reverse('planning.views.admin_index'))
        self.assertEqual(response.status_code, 200)

        # Test create plan view
        response = client.get(reverse('planning.views.create_plan'))
        self.assertEqual(response.status_code, 200)

        # Test copy plan view
        response = client.get(reverse('planning.views.copy_plan'))
        self.assertEqual(response.status_code, 200)

        # Test update plan view
        response = client.get(reverse('planning.views.update_plan', kwargs={'semester': 1127, 'plan_slug': 'Offering-Alpha---Burnaby'}))
        self.assertEqual(response.status_code, 200)

        # Test edit plan view
        response = client.get(reverse('planning.views.edit_plan', kwargs={
                'semester': 1127,
                'plan_slug': 'Offering-Alpha---Burnaby'
        }))
        self.assertEqual(response.status_code, 200)

        # Test assign instructor view
        response = client.get(reverse('planning.views.view_instructors', kwargs={
            'semester': 1127,
            'plan_slug': 'Offering-Alpha---Burnaby',
            'planned_offering_slug': 'CMPT-102-D100'
        }))
        self.assertEqual(response.status_code, 200)

        # Test edit planned offering view
        response = client.get(reverse('planning.views.edit_planned_offering', kwargs={
            'semester': 1127,
            'plan_slug': 'Offering-Alpha---Burnaby',
            'planned_offering_slug': 'CMPT-102-D100'
        }))
        self.assertEqual(response.status_code, 200)

        # Test manage courses view
        response = client.get(reverse('planning.views.manage_courses'))
        self.assertEqual(response.status_code, 200)

        # Test create courses view
        response = client.get(reverse('planning.views.create_course'))
        self.assertEqual(response.status_code, 200)

        # Test edit course view
        response = client.get(reverse('planning.views.edit_course', kwargs={'course_slug': 'CMPT-102'}))
        self.assertEqual(response.status_code, 200)

        # Test semester teaching plan view
        response = client.get(reverse('planning.views.view_intentions'))
        self.assertEqual(response.status_code, 200)

        # Test create semester teaching plan view
        response = client.get(reverse('planning.views.planner_create_intention'))
        self.assertEqual(response.status_code, 200)
        

    def test_that_planning_admin_returns_403_forbidden(self):
        """
        Tests basic page authentication for instructor
        """
        client = Client()
        client.login(ticket="ggbaker", service=CAS_SERVER_URL)
        response = client.get(reverse('planning.views.admin_index'))
        self.assertEqual(response.status_code, 403)