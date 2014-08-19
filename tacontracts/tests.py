# Python
import decimal
import datetime
# Django
from django.test import TestCase
# Local
from coredata.models import Unit, Person, Semester, Course, CourseOffering, \
                            Member
from ra.models import Account
# App
from .models import ContractFrozen, HiringSemester, TACategory, TAContract, \
                    TACourse

class TAContractTestCase(TestCase):
    def setUp(self):
        """
            Build a TACategory, TAContract, and two TACourses
        """
        unit = Unit(label="TEST", name="A Fake Unit for Testing") 
        unit.save()
        person = Person(emplid="300000000",
                        userid="testy",
                        first_name="Testy",
                        last_name="Testerson")
        person.save()
        semester = Semester(name="1147",
                            start=datetime.date.today(),
                            end=datetime.date.today())
        semester.save()
        course1 = Course(subject="TEST", 
                        number="100",
                        title="Intro to Testing")
        course1.save()
        course2 = Course(subject="TEST", 
                        number="200",
                        title="Advanced Testing")
        course2.save()
        courseoffering1 = CourseOffering(subject="TEST",
                                         number="100",
                                         section="D100",
                                         semester=semester,
                                         component="LEC",
                                         owner=unit,
                                         title="Intro to Testing",
                                         campus="BRNBY",
                                         enrl_cap=100,
                                         enrl_tot=100,
                                         wait_tot=50,
                                         course=course1)
        courseoffering1.save()
        courseoffering2 = CourseOffering(subject="TEST",
                                         number="200",
                                         section="D200",
                                         semester=semester,
                                         component="LEC",
                                         owner=unit,
                                         title="Advanced Testing",
                                         campus="BRNBY",
                                         enrl_cap=100,
                                         enrl_tot=100,
                                         wait_tot=50,
                                         course=course2)
        courseoffering2.save()
        account = Account(unit=unit, 
                          account_number=1337, 
                          position_number=5,
                          title="A Fake Account for Testing")
        account.save()
        four_weeks_later = datetime.date.today() + datetime.timedelta(days=28)
        hiring_semester = HiringSemester(semester=semester,
                                  unit=unit,
                                  deadline_for_acceptance=datetime.date.today(),
                                  pay_start=datetime.date.today(),
                                  pay_end=four_weeks_later,
                                  payperiods=2.5)
        hiring_semester.save()
        category = TACategory(account=account,
                              hiring_semester=hiring_semester,
                              code="TST",
                              title="Test Contract Category",
                              hours_per_bu=decimal.Decimal("42"),
                              holiday_hours_per_bu=decimal.Decimal("1.1"),
                              pay_per_bu=decimal.Decimal("100.00"),
                              scholarship_per_bu=decimal.Decimal("25.00"),
                              bu_lab_bonus=decimal.Decimal("0.17"))
        category.save()
        contract = TAContract(category=category,
                              person=person,
                              status="NEW",
                              sin="123456789",
                              deadline_for_acceptance=datetime.date.today(),
                              pay_start=datetime.date.today(),
                              pay_end=datetime.date.today() + datetime.timedelta(days=10),
                              payperiods=2.5,
                              appointment="INIT",
                              conditional_appointment=True,
                              created_by="classam",
                              tssu_appointment=True)
        contract.save()
        tacourse = TACourse(course=courseoffering1,
                            contract=contract,
                            bu=decimal.Decimal('3.0'),
                            labtut=True)
        tacourse.save()
        tacourse2 = TACourse(course=courseoffering2,
                             contract=contract,
                             bu=decimal.Decimal('2.0'),
                             labtut=False)
        tacourse2.save()
    
    def get_semester(self):
        return HiringSemester.objects.all()[0]

    def get_contract(self):
        return TAContract.objects.all()[0]
    
    def get_category(self):
        return TACategory.objects.all()[0]
   
    def get_courseoffering(self):
        return CourseOffering.objects.get(number="100")

    def test_tacategory_exists(self):
        category = TAContract.objects.all()
        self.assertEqual(len(category), 1)

    def test_visible_categories(self):
        semester = self.get_semester()
        visible = TACategory.objects.visible(semester)
        self.assertEqual(len(visible), 1)
    
    def test_tacontract_exists(self):
        contract = TAContract.objects.all()
        self.assertEqual(len(contract), 1)

    def test_visible_contracts(self):
        semester = self.get_semester()
        visible = TAContract.objects.visible(semester)
        self.assertEqual(len(visible), 1)

    def test_total_bu(self):
        """
        3.0 for Course 1, 0.17 for Course 1's Labtut, 2.0 for Course 2
        """
        contract = self.get_contract()
        self.assertEqual(type(contract.total_bu), type(decimal.Decimal("0")))
        self.assertEqual(contract.total_bu, decimal.Decimal("5.17"))

    def test_total_pay(self):
        """
        5.17 * 100/BU = $517.00
        """
        contract = self.get_contract()
        self.assertEqual(type(contract.total_pay), type(decimal.Decimal("0")))
        self.assertEqual(contract.total_pay, decimal.Decimal("517.00"))

    def test_scholarship_pay(self):
        """
        5.00 (no Bonus BU for scholarship pay, according to Tracy) * 25/BU = $125
        """
        contract = TAContract.objects.all()[0]
        contract = self.get_contract()
        self.assertEqual(type(contract.scholarship_pay), type(decimal.Decimal("0")))
        self.assertEqual(contract.scholarship_pay, decimal.Decimal("125"))

    def test_payperiods_and_biweekly(self):
        """
        Okay, so, $517 total_pay divided across 2.5 payperiods should be...
        """
        contract = self.get_contract()
        self.assertEqual(contract.payperiods, decimal.Decimal("2.5"))
        self.assertEqual(contract.biweekly_pay, decimal.Decimal("206.80"))
        self.assertEqual(contract.biweekly_scholarship, decimal.Decimal("50"))
    
    def test_tacourse_exists(self):
        course = TACourse.objects.all()
        self.assertEqual(len(course), 2)

    def delete_courses(self):
        contract = self.get_contract()
        courses = contract.course.all()
        for course in courses:
            course.delete()

    def test_total_bu_empty(self):
        self.delete_courses()
        contract = self.get_contract()
        self.assertEqual(contract.total_bu, decimal.Decimal("0"))

    def test_total_pay_empty(self):
        self.delete_courses()
        contract = self.get_contract()
        self.assertEqual(contract.total_pay, decimal.Decimal("0"))

    def sign_contract(self):
        contract = self.get_contract()
        contract.sign()

    def cancel_contract(self):
        contract = self.get_contract()
        contract.cancel()

    def test_sign_contract(self):
        self.sign_contract()
        contract = self.get_contract()
        self.assertEqual(contract.status, "SGN")

    def test_can_edit_draft_contract(self):
        category = self.get_category() 
        category.config["hello"] = "kitty"
        category.save()
        category = self.get_category()
        self.assertTrue("hello" in category.config)

    def test_can_delete_draft_contract(self):
        contract = self.get_contract()
        contract.delete()

    def test_cant_edit_signed_contract(self):
        """
        Can't edit a contract after it has been signed.
        """
        self.sign_contract()
        contract = self.get_contract()
        contract.config["hello"] = "bears"
        with self.assertRaises(ContractFrozen) as context:
            contract.save()

    def test_cant_delete_signed_contract(self):
        self.sign_contract()
        contract = self.get_contract()
        with self.assertRaises(ContractFrozen) as context:
            contract.delete()

    def test_cant_edit_signed_category(self):
        """
        Can't edit a category if it has a signed contract within it. 
        """
        self.sign_contract()
        category = self.get_category()
        category.config["hello"] = "kitty"
        with self.assertRaises(ContractFrozen) as context:
            category.save()

    def test_cant_delete_signed_category(self):
        self.sign_contract()
        category = self.get_category()
        with self.assertRaises(ContractFrozen) as context:
            category.delete()
    
    def test_can_hide_signed_category(self):
        self.sign_contract()
        category = self.get_category()
        category.hide()

        semester = self.get_semester()
        visible = TACategory.objects.visible(semester)
        self.assertEqual(len(visible), 0)

    def test_cant_edit_signed_course(self):
        """
        Can't edit a course if it has a signed contract as its parent.
        """
        self.sign_contract()
        contract = self.get_contract()
        course = TACourse.objects.filter(contract=contract)[0]
        course.config["hello"] = "bears"
        with self.assertRaises(ContractFrozen) as context:
            course.save()
    
    def test_cant_add_course_to_signed_contract(self):
        self.delete_courses()
        self.sign_contract()
        contract = self.get_contract()
        courseoffering = self.get_courseoffering()
        tacourse = TACourse(course=courseoffering,
                            contract=contract,
                            bu=decimal.Decimal('3.0'),
                            labtut=True)
        with self.assertRaises(ContractFrozen) as context:
            tacourse.save()


    def test_course_cant_be_deleted_if_contract_signed(self):
        """
        Can't delete a course if it has a signed contract as its parent.
        """
        self.sign_contract()
        contract = self.get_contract()
        course = TACourse.objects.filter(contract=contract)[0]
        with self.assertRaises(ContractFrozen) as context:
            course.delete()
    
    def test_can_delete_course_if_contract_draft(self):
        contract = self.get_contract()
        course = TACourse.objects.filter(contract=contract)[0]
        course.delete()

    def test_cancelling_draft_just_deletes_it(self):
        self.cancel_contract()
        contract = TAContract.objects.all()
        self.assertEqual(len(contract), 0)

    def test_deleting_contract_deletes_all_courses(self):
        self.cancel_contract()
        course = TACourse.objects.all()
        self.assertEqual(len(course), 0)

    def test_cancelling_signed_contract_changes_status(self):
        self.sign_contract()
        self.cancel_contract()
        contract = self.get_contract()
        self.assertEqual(contract.status, "CAN")

    def test_cancelled_contract_is_frozen(self):
        self.sign_contract()
        self.cancel_contract()
        category = self.get_category()
        contract = self.get_contract()
        course = TACourse.objects.all()[0]
        with self.assertRaises(ContractFrozen) as context:
            category.save()
        with self.assertRaises(ContractFrozen) as context:
            category.delete()
        with self.assertRaises(ContractFrozen) as context:
            contract.save()
        with self.assertRaises(ContractFrozen) as context:
            contract.delete()
        with self.assertRaises(ContractFrozen) as context:
            course.save()
        with self.assertRaises(ContractFrozen) as context:
            course.delete()
    
    def test_query_helpers(self):
        semester = self.get_semester()
        
        draft = TAContract.objects.draft(semester)
        signed = TAContract.objects.signed(semester)
        cancelled = TAContract.objects.cancelled(semester)
        self.assertEqual(len(draft), 1)
        self.assertEqual(len(signed), 0)
        self.assertEqual(len(cancelled), 0)

        self.sign_contract()
        draft = TAContract.objects.draft(semester)
        signed = TAContract.objects.signed(semester)
        cancelled = TAContract.objects.cancelled(semester)
        self.assertEqual(len(draft), 0)
        self.assertEqual(len(signed), 1)
        self.assertEqual(len(cancelled), 0)

        self.cancel_contract()
        draft = TAContract.objects.draft(semester)
        signed = TAContract.objects.signed(semester)
        cancelled = TAContract.objects.cancelled(semester)
        self.assertEqual(len(draft), 0)
        self.assertEqual(len(signed), 0)
        self.assertEqual(len(cancelled), 1)

    def test_copy(self):
        contract = self.get_contract()
        self.sign_contract()
        newcontract = contract.copy("username")
        newcourses = TACourse.objects.filter(contract=newcontract)
        self.assertEqual(newcontract.status, "NEW")
        self.assertEqual(len(newcourses), 2)
        self.assertEqual(newcontract.created_by, "username")
        self.assertEqual(newcourses[0].total_bu, decimal.Decimal('3.17'))

    def test_member_creation(self):
        offering = self.get_courseoffering()
        contract = self.get_contract()
        members = Member.objects.filter(person=contract.person, 
                                        role='TA',
                                        offering=offering)
        self.assertEqual(len(members), 0)

        self.sign_contract()
        members = Member.objects.filter(person=contract.person, 
                                        role='TA',
                                        offering=offering)
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].added_reason, 'CTA') 
        self.assertEqual(len(members[0].tacourse.all()), 1)

        self.cancel_contract()
        members = Member.objects.filter(person=contract.person, 
                                        role='TA',
                                        offering=offering)
        dropped_members = Member.objects.filter(person=contract.person, 
                                                offering=offering, 
                                                role='DROP')
        self.assertEqual(len(members), 0)
        self.assertEqual(len(dropped_members), 1)


    def test_hours(self):
        contract = self.get_contract()
        course = contract.course.all()[0]
        self.assertEqual(course.holiday_hours, decimal.Decimal('3.3'))
        self.assertEqual(course.hours, decimal.Decimal('126'))

