"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

# Django
from django.test import TestCase
from django.db import IntegrityError


# CourSys
from .models import GradeSource
from .models import DiscreteRule
from .models import ContinuousRule


# Built-In
import decimal


class GradeSourceTest(TestCase):
    def setUp(self):
        self.gs1 = GradeSource.objects.create(country='NZ', institution='University of Wellington')
        self.gs2 = GradeSource.objects.create(country='FR', institution='Universite de Paris')

    def test_auto_slug(self):
        """
        Tests that autoslug gets properly generated.
        """
        gs = GradeSource.objects.create(country='CA', institution='UBC')
        self.assertEqual(gs.slug, "ubc-ca")

    def test_unique_gs_pairs(self):
        """
        Tests that unique_together country and institution is enforced.
        """
        with self.assertRaises(IntegrityError):
            gs = GradeSource(country='CA', institution='UBC')
            gs1 = GradeSource(country='CA', institution='UBC')

            gs.save()
            gs1.save()


class DiscreteRuleTest(TestCase):
    def setUp(self):
        self.gs1 = GradeSource.objects.create(country='NZ', institution='University of Wellington')

    def test_bad_transfer_value_decimal(self):
        """
        Tests bad decimal value 1000.44 for 'transfer_value' field.
        """
        with self.assertRaises(decimal.InvalidOperation):
            dr = DiscreteRule.objects.create(grade_source=self.gs1,
                                             lookup_value="Penguin",
                                             transfer_value=decimal.Decimal("1000.44"))
    
    def test_good_transfer_value_decimal(self):
        """
        Tests decimal value 4.33 for 'transfer_value' field.
        """
        dr = DiscreteRule.objects.create(grade_source=self.gs1,
                                         lookup_value="Penguin",
                                         transfer_value=decimal.Decimal("4.33"))
