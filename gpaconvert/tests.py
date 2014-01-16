import decimal

from django.db import IntegrityError
from django.test import TestCase

from gpaconvert.models import GradeSource
from gpaconvert.models import DiscreteRule


class GradeSourceTest(TestCase):
    def setUp(self):
        self.gs1 = GradeSource.objects.create(country='NZ', institution='University of Wellington')
        self.gs2 = GradeSource.objects.create(scale='CONT', country='FR',
                                              institution='Universite de Paris')

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
        gs = GradeSource(country='CA', institution='UBC')
        gs1 = GradeSource(country='CA', institution='UBC')

        gs.save()
        with self.assertRaises(IntegrityError):
            gs1.save()

    def test_get_rule_success(self):
        """
        Tests that get_rule can successfully retrieve a rule of both types.
        """
        # Discrete Rules
        self.gs1.discrete_rules.create(lookup_value='some string', transfer_value='A')
        self.gs1.discrete_rules.create(lookup_value='another string', transfer_value='C')

        discrete_rule = self.gs1.get_rule('another string')
        self.assertEqual(discrete_rule, self.gs1.discrete_rules.get(id=2))

        # Continuous Rules
        self.gs2.continuous_rules.create(lookup_lbound=90, transfer_value='A')
        self.gs2.continuous_rules.create(lookup_lbound=50, transfer_value='C')

        continuous_rule = self.gs2.get_rule(50)
        self.assertEqual(continuous_rule, self.gs2.continuous_rules.get(id=2))

    def test_get_rule_not_found(self):
        """
        Tests that get_rule will return None if no suitable rule is found.
        """
        # Discrete Rules
        self.gs1.discrete_rules.create(lookup_value='some string', transfer_value='A')
        self.gs1.discrete_rules.create(lookup_value='another string', transfer_value='C')

        discrete_rule = self.gs1.get_rule('I do not exist')
        self.assertIsNone(discrete_rule)

        # Continuous Rules
        self.gs2.continuous_rules.create(lookup_lbound=90, transfer_value='A')
        self.gs2.continuous_rules.create(lookup_lbound=50, transfer_value='C')

        continuous_rule = self.gs2.get_rule(40)
        self.assertIsNone(continuous_rule)


class DiscreteRuleTest(TestCase):
    def setUp(self):
        self.gs1 = GradeSource.objects.create(country='NZ', institution='University of Wellington')

    def not_a_test_bad_transfer_value_decimal(self):
        """
        Tests bad decimal value 1000.44 for 'transfer_value' field.
        """
        with self.assertRaises(decimal.InvalidOperation):
            dr = DiscreteRule.objects.create(grade_source=self.gs1,
                                             lookup_value="Penguin",
                                             transfer_value='asdfasdf')

    def test_good_transfer_value_decimal(self):
        """
        Tests decimal value 4.33 for 'transfer_value' field.
        """
        dr = DiscreteRule.objects.create(grade_source=self.gs1,
                                         lookup_value="Penguin",
                                         transfer_value=decimal.Decimal("4.33"))
