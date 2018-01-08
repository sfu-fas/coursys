from django.test import TestCase
from visas.models import Visa
from coredata.models import Person, Semester, VISA_STATUSES
from datetime import date, timedelta


# Very simple tests to make sure at least our expiration calculations are correct.
class VisaTestCase(TestCase):
    fixtures = ['basedata', 'coredata']

    def setUp(self):
        p1 = Person(emplid=210012345, userid="test1",
                last_name="Lname", first_name="Fname", pref_first_name="Fn", middle_name="M")
        p1.save()

    def testApplication(self):
        p = Person.objects.get(emplid=210012345)
        # Create three visas, one that should be expired, one that will soon, and one that is valid.
        v1 = Visa(person=p, status=VISA_STATUSES[0][0], start_date=date(2000,0o1,0o1), end_date=date(2000,0o1,0o1))
        v2 = Visa(person=p, status=VISA_STATUSES[0][0], start_date=date(2000,0o1,0o1), end_date=date(2099,0o1,0o1))
        next_semester = Semester.next_starting()
        almost_expired_date = next_semester.end - timedelta(days=5)
        v3 = Visa(person=p, status=VISA_STATUSES[0][0], start_date=date(2000,0o1,0o1), end_date=almost_expired_date)

        self.assertEqual(v1.is_valid(), False)
        self.assertEqual(v1.is_expired(), True)
        self.assertEqual(v1.is_almost_expired(), False)
        self.assertEqual(v2.is_valid(), True)
        self.assertEqual(v2.is_expired(), False)
        self.assertEqual(v2.is_almost_expired(), False)
        self.assertEqual(v3.is_valid(), True)
        self.assertEqual(v3.is_expired(), False)
        self.assertEqual(v3.is_almost_expired(), True)


