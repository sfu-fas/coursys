# Python
# Python
import datetime
import decimal
# Django
from django.db import models, transaction
from django.db.models.query import QuerySet
# Third Party
from autoslug import AutoSlugField
# Local
from coredata.models import Unit, Person, CourseOffering, Semester, Member
from courselib.slugs import make_slug
from courselib.json_fields import JSONField
from grad.models import GradStudent
from ra.models import Account
from dashboard.models import NewsItem


CONTRACT_STATUS_CHOICES = (
        ("NEW","Draft"),
        ("SGN","Signed"),
        ("CAN","Cancelled"),
)


class ContractFrozen(Exception):
    """
    Once a SGNed contract exists within a Category, that Category
        can never be changed again, except to hide it. 
    Once a contract is in the SGN or CAN state, it can't be edited.
        (Except for the state, which can be moved from SGN to CAN).
    To edit a contract that is SGN, that contract must be CANcelled, 
        then copied, then SiGNed again. 
    Movement between the status options is one-way - 
        a NEW contract can become a SGN contract,
        and a SGN contract can become a CAN contract, 
        but a SGN contract can't be changed to a NEW,
        nor can a CAN contract be changed to NEW or SGN.
    """
    pass


class NoPreviousSemesterException(Exception):
    """
    This is thrown when you try to copy the TACategory objects
    from a previous TASemester, but no such TASemester can be 
    found. 
    """
    pass


APPOINTMENT_CHOICES = (
        ("INIT","Initial appointment to this position"),
        ("REAP","Reappointment to same position or revision to appointment"),
)


# These are SIN numbers that we know are probably fake.
DUMMY_SINS = ['999999999', '000000000', '123456789']


class HiringSemesterManager(models.Manager):
    def visible(self, units):
        qs = self.get_queryset()
        return qs.filter(unit__in=units)

    def semester(self, semester_name, units):
        qs = self.get_queryset()
        return qs.filter(unit__in=units,
                         semester=Semester.objects.get(name=semester_name))


class TACategoryManager(models.Manager):
    def visible(self, hiring_semester):
        qs = self.get_queryset()
        return qs.filter(hiring_semester=hiring_semester, hidden=False)


class TAContractManager(models.Manager):
    def visible(self, hiring_semester):
        qs = self.get_queryset()
        return qs.filter(category__hiring_semester=hiring_semester)\
                         .select_related('category')\
                         .prefetch_related('course')

    def draft(self, hiring_semester):
        return self.visible(hiring_semester).filter(status='NEW')

    def signed(self, hiring_semester):
        return self.visible(hiring_semester).filter(status='SGN')

    def cancelled(self, hiring_semester):
        return self.visible(hiring_semester).filter(status='CAN')


class HiringSemester(models.Model):
    """
    TA Appointments tend to be a semesterly affair, and each Contract in 
    a Semester is likely to share a single pay_start, pay_end, and set
    of payperiods. 
    This is subject to change on a contract-by-contract basis, 
    so these are only defaults. 
    """
    semester = models.ForeignKey(Semester, on_delete=models.PROTECT)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    deadline_for_acceptance = models.DateField()
    pay_start = models.DateField()
    pay_end = models.DateField()
    payperiods = models.DecimalField(max_digits=4, decimal_places=2,
                                     verbose_name= "During the contract, how many bi-weekly pay periods?")
    config = JSONField(null=False, blank=False, editable=False, default=dict)
    
    class Meta:
        unique_together = (('semester', 'unit'),)
    
    def __str__(self):
        return str(self.semester.name)

    def copy_categories_from_previous_semester(self, unit):
        prev_semester = self.semester.previous_semester()
        if prev_semester == None:
            raise NoPreviousSemesterException()
        try:
            hiring_semester = HiringSemester.objects.get(semester=prev_semester, unit=unit)
        except HiringSemester.DoesNotExist:
            raise NoPreviousSemesterException()

        for category in hiring_semester.tacategory_set.all():
            category.copy_to_new_semester(self)
        
    @property
    def contracts(self):
        return TAContract.objects.visible(self)

    @property
    def number_of_contracts(self):
        return len(self.contracts)

    @property
    def number_of_incomplete_contracts(self):
        incomplete_contracts = [contract for contract in self.contracts 
                                if contract.status == 'NEW']
        return len(incomplete_contracts)

    @property
    def total_bu(self):
        return sum([contract.total_bu for contract in self.contracts])
    
    objects = HiringSemesterManager()
    
    def next_export_seq(self):
        """
        For the CSV, 
        we keep track of which batch of exports we're currently on.
        """
        if 'export_seq' in self.config:
            current = self.config['export_seq']
        else:
            current = 0
        
        self.config['export_seq'] = current + 1
        self.save()
        return self.config['export_seq']


class TACategory(models.Model):
    """
    A TACategory details a pay category.
    It's only valid for a single semester, but we offer the ability 
    to copy all of the TACategories from the last semester to the next semester.
    """
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    # the account already FKs to a Unit, so we don't need one. 
    hiring_semester = models.ForeignKey(HiringSemester, editable=False, on_delete=models.PROTECT)
    code = models.CharField(max_length=5, 
                        help_text="Category Choice Code - for example 'GTA2'")
    title = models.CharField(max_length=50,
                        help_text="Category Choice Title - for example 'PhD'")
    pay_per_bu = models.DecimalField(max_digits=8,
                                     decimal_places=2, 
                                     verbose_name="Default pay, "+\
                                                  "per base unit")
    scholarship_per_bu = models.DecimalField(max_digits=8, 
                                             decimal_places=2, 
                                             verbose_name="Scholarship pay, "+\
                                                          "per base unit",)
    bu_lab_bonus = models.DecimalField(max_digits=8,
                                       decimal_places=2, 
                                       default=decimal.Decimal('0.17'),
                                       verbose_name="Bonus BUs awarded to a "+\
                                                    "course with a lab")
    hours_per_bu = models.DecimalField(max_digits=6,
                                       decimal_places=2, 
                                       default=decimal.Decimal('42'),
                                       verbose_name="Hours per BU")

    holiday_hours_per_bu = models.DecimalField(max_digits=4,
                                               decimal_places=2, 
                                               default=decimal.Decimal('1.1'),
                                               verbose_name="Holiday hours per BU")

    # ensc-gta2
    def autoslug(self):
        return make_slug(self.account.unit.label + '-' + str(self.code))
    slug = AutoSlugField(populate_from='autoslug',
                         null=False, 
                         editable=False, 
                         unique=True)
    created = models.DateTimeField(default=datetime.datetime.now,
                                   editable=False)
    hidden = models.BooleanField(default=False, editable=False)
    config = JSONField(null=False, blank=False, editable=False, default=dict)

    objects = TACategoryManager()
    
    def __str__(self):
        return "%s %s %s - %s" % (self.account.unit.label, str(self.code), 
                                  str(self.title), str(self.account))

    @property
    def frozen(self):
        """
        If any of the contracts in this category are SGN or CAN, this
        category can never be changed, only hidden. 
        """
        bools = [contract.frozen for contract in self.contract.all()]
        return True in bools

    def save(self, always_allow=False, *args, **kwargs):
        if not always_allow and self.frozen:
            raise ContractFrozen()
        else:
            super(TACategory, self).save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        if self.frozen:
            raise ContractFrozen()
        else:
            super(TACategory, self).delete(*args, **kwargs)

    def hide(self):
        self.hidden = True
        self.save(always_allow=True)

    def copy_to_new_semester(self, new_hiring_semester):
        cat = TACategory(account=self.account,
                         hiring_semester=new_hiring_semester,
                         code=self.code,
                         title=self.title,
                         pay_per_bu=self.pay_per_bu,
                         scholarship_per_bu=self.scholarship_per_bu,
                         bu_lab_bonus=self.bu_lab_bonus)
        cat.save()
        return cat


class TAContract(models.Model):
    """    
    TA Contract, filled in by TA Administrator
    """
    person = models.ForeignKey(Person, on_delete=models.PROTECT)
    category = models.ForeignKey(TACategory, on_delete=models.PROTECT,
                                 related_name="contract")
    status = models.CharField(max_length=4,
                              choices=CONTRACT_STATUS_CHOICES,
                              default="NEW",
                              editable=False)
    sin = models.CharField(max_length=30, 
                           verbose_name="SIN",
                           help_text="Social Insurance Number - 000000000 if unknown")

    # We want do add some sort of accountability for checking visas.  Don't
    # allow printing of the contract if this box hasn't been checked.
    visa_verified = models.BooleanField(default=False, help_text="I have verified this TA's visa information")
    deadline_for_acceptance = models.DateField()
    appointment_start = models.DateField(null=True, blank=True)
    appointment_end = models.DateField(null=True, blank=True)
    pay_start = models.DateField()
    pay_end = models.DateField()
    payperiods = models.DecimalField(max_digits=4, decimal_places=2,
                                     verbose_name= "During the contract, how many bi-weekly pay periods?")
    appointment = models.CharField(max_length=4, 
                            choices=APPOINTMENT_CHOICES, 
                            default="INIT")
    conditional_appointment = models.BooleanField(default=False)
    tssu_appointment = models.BooleanField(default=True)
    
    # this is really only important if the contract is in Draft status
    # if Signed, the student's acceptance is implied. 
    # if Cancelled, the student's acceptance doesn't matter. 
    accepted_by_student = models.BooleanField(default=False, 
                  help_text="Has the student accepted the contract?")

    comments = models.TextField(blank=True)
    # curtis-lassam-2014-09-01 
    def autoslug(self):
        return make_slug(self.person.first_name + '-' + self.person.last_name \
                            + "-" + str(self.pay_start))
    slug = AutoSlugField(populate_from='autoslug',
                         null=False, 
                         editable=False, 
                         unique=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    created_by = models.CharField(max_length=20, null=False, blank=False, \
                                  editable=False)
    config = JSONField(null=False, blank=False, editable=False, default=dict)
    
    objects = TAContractManager()
   
    def __str__(self):
        return "%s" % (self.person,)

    @property
    def frozen(self):
        """
        Returns True when this contract is uneditable. 
        """
        return self.status != 'NEW'

    def save(self, always_allow=False, *args, **kwargs):
        if not always_allow and self.frozen:
            raise ContractFrozen()
        else:
            super(TAContract, self).save(*args, **kwargs)
            self.set_grad_student_sin()
            self.sync_course_member()

    def sign(self):
        """
        Moves the contract from "Draft" to "Contract Signed"
        """
        self.status = 'SGN'
        self.save(always_allow=True)

    def cancel(self):
        """
        Moves the contract from "Contract Signed" to "Cancelled"
        or
        Moves the contract from "New" to *deleted*
        """
        if self.frozen:
            self.status = 'CAN'
            self.save(always_allow=True)
        else:
            self.delete()
    
    def set_grad_student_sin(self):
        """
        Sets the SIN of the GradStudent object, if it exists and hasn't
        already been set. 
        """
        for gs in GradStudent.objects.filter(person=self.person):
            if (('sin' not in gs.config 
                or ('sin' in gs.config and gs.config['sin'] in DUMMY_SINS)) 
                and not self.sin in DUMMY_SINS):
                gs.person.set_sin(self.sin)
                gs.person.save()

    def delete(self, *args, **kwargs):
        if self.frozen:
            raise ContractFrozen()
        else:
            for course in self.course.all():
                course.delete()
            super(TAContract, self).delete(*args, **kwargs)

    def copy(self, created_by):
        """
            Return a copy of this contract, but with status="NEW"
        """
        newcontract = TAContract(person=self.person,
                                 category=self.category,
                                 sin=self.sin,
                                 deadline_for_acceptance= \
                                        self.deadline_for_acceptance,
                                 appointment_start=self.appointment_start,
                                 appointment_end=self.appointment_end,
                                 pay_start=self.pay_start,
                                 pay_end=self.pay_end,
                                 payperiods=self.payperiods,
                                 created_by=created_by,
                                 appointment=self.appointment,
                                 conditional_appointment= \
                                         self.conditional_appointment,
                                 tssu_appointment=self.tssu_appointment,
                                 comments = self.comments)
        newcontract.save()
        for course in self.course.all():
            newcourse = TACourse(course=course.course, 
                                 contract=newcontract,
                                 bu=course.bu, 
                                 labtut=course.labtut)
            newcourse.save()
        return newcontract

    
    @property
    def pay_per_bu(self):
        return self.category.pay_per_bu
    
    @property
    def scholarship_per_bu(self):
        return self.category.scholarship_per_bu

    @property
    def bu_lab_bonus(self):
        return self.category.bu_lab_bonus
    
    @property
    def bu(self):
        if len(self.course.all()) == 0:
            return decimal.Decimal(0)
        else:
            return sum( [course.bu for course in self.course.all()] )

    @property
    def total_bu(self):
        if len(self.course.all()) == 0:
            return decimal.Decimal(0)
        else:
            return sum( [course.total_bu for course in self.course.all()] )
    
    @property
    def total_pay(self):
        if len(self.course.all()) == 0:
            return decimal.Decimal(0)
        else:
            return decimal.Decimal(self.total_bu * self.pay_per_bu)

    @property
    def biweekly_pay(self):
        if self.payperiods == 0:
            return decimal.Decimal(0)
        return self.total_pay / decimal.Decimal(self.payperiods)

    @property
    def scholarship_pay(self):
        if len(self.course.all()) == 0:
            return decimal.Decimal(0)
        else:
            return self.bu * self.scholarship_per_bu

    @property
    def biweekly_scholarship(self):
        if self.payperiods == 0:
            return decimal.Decimal(0)
        return self.scholarship_pay / decimal.Decimal(self.payperiods)

    @property
    def total(self):
        return self.total_pay + self.scholarship_pay

    @property
    def number_of_emails(self):
        return len(self.email_receipt.all())


    def grad_students(self):
        """ 
        Fetch the GradStudent record associated with this student in this
        semester.
        """
        students = GradStudent.get_canonical(self.person, self.category.hiring_semester.semester)
        return students

    @property
    def should_be_added_to_the_course(self):
        return (self.status == "SGN" or self.accepted_by_student == True) and not (self.status == "CAN")

    @classmethod
    def update_ta_members(cls, person, semester_id):
        """
        Update all TA memberships for this person+semester.

        Idempotent.
        """
        from ta.models import TACourse as OldTACourse

        def add_membership_for(tacrs, reason, memberships):
            if not tacrs.contract.should_be_added_to_the_course or tacrs.total_bu <= 0:
                return

            # Find existing membership for this person+offering if it exists
            # (Behaviour here implies you can't be both TA and other role in one offering: I'm okay with that.)
            for m in memberships:
                if m.person == person and m.offering == tacrs.course:
                    break
            else:
                # there was no membership: create
                m = Member(person=person, offering=tacrs.course)
                memberships.append(m)

            m.role = 'TA'
            m.credits = 0
            m.career = 'NONS'
            m.added_reason = reason
            m.config['bu'] = str(tacrs.total_bu)


        with transaction.atomic():
            memberships = Member.objects.filter(person=person, offering__semester_id=semester_id)
            memberships = list(memberships)

            # drop any TA memberships that should be re-added below
            for m in memberships:
                if m.role == 'TA' and m.added_reason in ['CTA', 'TAC']:
                    m.role = 'DROP'

            # tacontracts memberships
            tacrses = TACourse.objects.filter(contract__person_id=person, course__semester_id=semester_id)
            for tacrs in tacrses:
                add_membership_for(tacrs, 'TAC', memberships)

            # ta memberships
            tacrses = OldTACourse.objects.filter(contract__application__person_id=person, course__semester_id=semester_id)
            for tacrs in tacrses:
                add_membership_for(tacrs, 'CTA', memberships)

            # save whatever just happened
            for m in memberships:
                m.save_if_dirty()


    def sync_course_member(self):
        """
        Once a contract is Signed, we should create a Member object for them.
        If a contract is Cancelled, we should DROP the Member object. 

        This operation should be idempotent - run it as many times as you
        want, the result should always be the same. 
        """
        TAContract.update_ta_members(self.person, self.category.hiring_semester.semester_id)

    def course_list_string(self):
        # Build a string of all course offerings tied to this contract for CSV downloads and grad student views.
        course_list_string = ', '.join(ta_course.course.name() for ta_course in self.course.all())
        return course_list_string


class CourseDescription(models.Model):
    """
    Description of the work for a TA contract
    """
    unit = models.ForeignKey(Unit, related_name='description_unit', on_delete=models.PROTECT)
    description = models.CharField(max_length=60, blank=False, null=False,
                                   help_text="Description of the work for a course, as it will appear on the contract. (e.g. 'Office/marking')")
    hidden = models.BooleanField(default=False)
    config = JSONField(null=False, blank=False, default=dict)

    def __str__(self):
        return self.description

    def delete(self):
        """Like most of our objects, we don't want to ever really delete it."""
        self.hidden = True
        self.save()

class TACourse(models.Model):
    course = models.ForeignKey(CourseOffering, on_delete=models.PROTECT,
                               blank=False, 
                               null=False,
                               related_name="+")
    contract = models.ForeignKey(TAContract, on_delete=models.PROTECT,
                                 blank=False, 
                                 null=False, 
                                 editable=False,
                                 related_name="course")
    bu = models.DecimalField(max_digits=4, 
                             decimal_places=2,
                             verbose_name="BUs",
                             help_text="The number of Base Units for this course.")
    labtut = models.BooleanField(default=False, 
                                 verbose_name="Lab/Tutorial?", 
                                 help_text="Does this course have a lab or tutorial?")
    description = models.ForeignKey(CourseDescription, null=True, blank=True, on_delete=models.PROTECT)
    member = models.ForeignKey(Member, null=True, editable=False, related_name="tacourse", on_delete=models.PROTECT)

    def autoslug(self):
        """
        curtis-lassam-2014-09-01 
        """
        return make_slug(self.course.slug)
    slug = AutoSlugField(populate_from='autoslug', 
                         null=False, 
                         editable=False, 
                         unique=False)
    config = JSONField(null=False, blank=False, editable=False, default=dict)
    
    class Meta:
        unique_together = (('contract', 'course'),)
    
    def __str__(self):
        return "Course: %s  TA: %s" % (self.course, self.contract)

    @property
    def frozen(self):
        return self.contract.frozen
    
    def save(self, always_allow=False, *args, **kwargs):
        if not always_allow and self.frozen:
            raise ContractFrozen()
        else:
            super(TACourse, self).save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        if self.frozen:
            raise ContractFrozen()
        else:
            super(TACourse, self).delete(*args, **kwargs)

    def has_labtut(self):
        # for consistent interface with ta.models.TACourse
        return self.labtut

    @property
    def prep_bu(self):
        """
        Return the prep BUs for this assignment
        """
        if self.labtut:
            return self.contract.bu_lab_bonus 
        else:
            return 0

    @property
    def total_bu(self):
        """
        Return the total BUs for this assignment
        """
        return self.bu + self.prep_bu
    
    @property
    def total_pay(self):
        return self.total_bu * self.contract.pay_per_bu

    @property
    def scholarship_pay(self):
        return self.bu * self.contract.scholarship_per_bu

    @property
    def total(self):
        return self.total_pay + self.scholarship_pay

    @property
    def holiday_hours_per_bu(self):
        return self.contract.category.holiday_hours_per_bu

    @property
    def holiday_hours(self):
        return self.bu * self.contract.category.holiday_hours_per_bu
    
    @property
    def hours(self):
        return self.bu * self.contract.category.hours_per_bu

    @property
    def hours_per_bu(self):
        return self.contract.category.hours_per_bu

    @property
    def min_tug_prep(self):
        """
        The fewest hours the instructor should be able to assign for "prep" in the TUG.

        Courses with labs/tutorials must used 1 BU for prep. In addition to the 0.17 BU that must be used for prep.
        That's a *totally* different kind of prep.
        """
        return self.hours_per_bu if self.labtut else 0


class EmailReceipt(models.Model):
    """ 
    The system offers the ability to bulk email notifications to contract holders.
    This object serves as a record that this has occurred, which we can consult
    later. 
    """
    contract = models.ForeignKey(TAContract, on_delete=models.PROTECT,
                                 blank=False, 
                                 null=False, 
                                 editable=False,
                                 related_name="email_receipt")
    content = models.ForeignKey(NewsItem, on_delete=models.PROTECT,
                                 blank=False,
                                 null=False,
                                 editable=False)
