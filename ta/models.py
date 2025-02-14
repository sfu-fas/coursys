import os
from django.db import models
from django.db.models import Sum
from coredata.models import Person, Member, Course, Semester, Unit ,CourseOffering, CAMPUS_CHOICES
from django.conf import settings
from ra.models import Account
from courselib.json_fields import JSONField
from courselib.json_fields import getter_setter
from courselib.slugs import make_slug
from autoslug import AutoSlugField
import decimal, datetime, uuid
from numbers import Number
from dashboard.models import NewsItem
from django.urls import reverse
from django.core.cache import cache
from django.utils.safestring import mark_safe
from django.http import HttpResponse
from dashboard.letters import ta_form
from django.core.mail import EmailMultiAlternatives
from courselib.markup import markup_to_html
from courselib.storage import UploadedFileStorage, upload_path
from django.template.loader import get_template
from grad.models import GradStudent, Supervisor, STATUS_REAL_PROGRAM
from . import bu_rules
from django.utils import timezone
from tacontracts.models import HiringSemester
from dashboard.letters import ta_evaluation_form

LAB_BONUS_DECIMAL = decimal.Decimal('0.17')
LAB_BONUS = float(LAB_BONUS_DECIMAL)
HOURS_PER_BU = 42 # also in media/js/ta.js
LAB_PREP_HOURS = 13 # min hours of prep for courses with tutorials/labs

HOLIDAY_HOURS_PER_BU = decimal.Decimal('1.1')

CMPT_WCOURSE_BU = decimal.Decimal('2')  # additional BU for writing course
CMPT_COURSE_BU = decimal.Decimal('1')

DEPT_CHOICES = [
    ('CMPT', 'CMPT student'),
    ('OTHR', 'Other program'),
    ('NONS', 'Not currently a student'),
]


def _round_hours(val):
    "Round to two decimal places because... come on."
    if isinstance(val, decimal.Decimal):
        return val.quantize(decimal.Decimal('.01'))
    elif isinstance(val, Number):
        return round(val, 2)
    else:
        return val


class TUG(models.Model):
    """
    Time use guideline filled out by instructors
    
    Based on form in Appendix C (p. 73) of the collective agreement:
    http://www.tssu.ca/wp-content/uploads/2010/01/CA-2004-2010.pdf
    """	
    member = models.OneToOneField(Member, null=False, on_delete=models.PROTECT)
    base_units = models.DecimalField(max_digits=4, decimal_places=2, blank=False, null=False)
    draft = models.BooleanField(null=False, default=False)    
    last_update = models.DateField(auto_now=True)
    config = JSONField(null=False, blank=False, default=dict) # addition configuration stuff:
        # t.config['prep']: Preparation for labs/tutorials
        # t.config['meetings']: Attendance at planning meetings with instructor
        # t.config['lectures']: Attendance at lectures
        # t.config['tutorials']: Attendance at labs/tutorials
        # t.config['office_hours']: Office hours/student consultation
        # t.config['grading']
        # t.config['test_prep']: Quiz/exam preparation and invigilation
        # t.config['holiday']: Holiday compensation
        # Each of the above is a dictionary like:
        #     {
        #     'weekly': 2.0,
        #     'total': 26.0,
        #     'note': 'if more is required, we can revisit',
        #     }
        # t.config['other1']
        # t.config['other2']
        # As the other fields, but adding 'label'.

        ########### Four duties are added on 2024.06        
        # t.config['prep_lectures']: Preparation for lectures
        # t.config['support']: Support classroom course delivery, including technical support
        # t.config['leading']: Leading discussions
        # t.config['e_communication']: Electronic communication
    
    prep = property(*getter_setter('prep'))
    meetings = property(*getter_setter('meetings'))
    lectures = property(*getter_setter('lectures'))
    tutorials = property(*getter_setter('tutorials'))
    office_hours = property(*getter_setter('office_hours'))
    grading = property(*getter_setter('grading'))
    test_prep = property(*getter_setter('test_prep'))
    holiday = property(*getter_setter('holiday'))
    other1 = property(*getter_setter('other1'))
    other2 = property(*getter_setter('other2'))

    prep_lectures = property(*getter_setter('prep_lectures'))
    support = property(*getter_setter('support'))
    leading = property(*getter_setter('leading'))
    e_communication = property(*getter_setter('e_communication'))
    
    def iterothers(self):
        return (other for key, other in self.config.items() 
                if key.startswith('other')
                and isinstance(other.get('total'), float)
                and other.get('total', 0) > 0)

    others = lambda self:list(self.iterothers())
    
    def iterfielditems(self):
        return ((field, self.config[field]) for field in self.new_all_fields 
                 if field in self.config)
        
    regular_fields = ['prep', 'meetings', 'lectures', 'tutorials',
            'office_hours', 'grading', 'test_prep', 'holiday']
    other_fields = ['other1', 'other2']
    all_fields = regular_fields + other_fields

    #defaults = dict([(field, {'weekly': 0, 'total': 0, 'comment': ''}) for field in regular_fields] +
    #    [(field, {'label': '', 'weekly': 0, 'total': 0, 'comment': ''}) for field in other_fields])

    new_regular_fields = ['prep', 'meetings', 'prep_lectures', 'lectures', 'support', 'tutorials',
            'leading', 'office_hours', 'e_communication', 'grading', 'test_prep', 'holiday']
    new_all_fields = new_regular_fields + other_fields
    
    defaults = dict([(field, {'weekly': 0, 'total': 0, 'comment': ''}) for field in new_regular_fields] +
        [(field, {'label': '', 'weekly': 0, 'total': 0, 'comment': ''}) for field in other_fields])

    # depicts the above comment in code
    config_meta = {'prep':{'label':'Preparation', 
                    'help':'1. Preparation for labs/tutorials'},
            'meetings':{'label':'Attendance at planning meetings', 
                    'help':'2. Attendance at planning/coordinating meetings with instructor'}, 
            'lectures':{'label':'Attendance at lectures', 
                    'help':'3. Attendance at lectures'}, 
            'tutorials':{'label':'Attendance at labs/tutorials', 
                    'help':'4. Attendance at labs/tutorials'}, 
            'office_hours':{'label':'Office hours', 
                    'help':'5. Office hours/student consultation/electronic communication'}, 
            'grading':{'label':'Grading', 
                    'help':'6. Grading\u2020',
                    'extra':'\u2020Includes grading of all assignments, reports and examinations.'}, 
            'test_prep':{'label':'Quiz/exam preparation and invigilation', 
                    'help':'7. Quiz preparation/assist in exam preparation/Invigilation of exams'}, 
            'holiday':{'label':'Holiday compensation', 
                    'help':'8. Statutory Holiday Compensation\u2021',
                    'extra':'''\u2021To compensate for all statutory holidays which  
may occur in a semester, the total workload required will be reduced by %s
hour(s) for each base unit assigned excluding the additional %s B.U. for
preparation, e.g. %s hours reduction for %s B.U. appointment.''' % (HOLIDAY_HOURS_PER_BU, LAB_BONUS, 4.4, 4+LAB_BONUS)}}
    
    # new version of TUG duties
    new_config_meta = {
            'prep':{'label':'Preparation for labs/tutorials/workshops', 
                    'help':'1. Preparation for labs/tutorials/workshops'},
            'meetings':{'label':'Attendance at orientation and planning/coodinating meetings with instructor', 
                    'help':'2. Attendance at orientation and planning/coodinating meetings with instructor'}, 
            'prep_lectures':{'label':'Preparation for lectures', 
                    'help':'3. Preparation for lectures'}, 
            'lectures':{'label':'Attendance at lectures, including breakout group', 
                    'help':'4. Attendance at lectures, including breakout group'}, 
            'support':{'label':'Support classroom course delivery, including technical support', 
                    'help':'5. Support classroom course delivery, including technical support'}, 
            'tutorials':{'label':'Attendance at labs/tutorials/workshops', 
                    'help':'6. Attendance at labs/tutorials/workshops'}, 
            'leading':{'label':'Leading discussions', 
                    'help':'7. Leading discussions'}, 
            'office_hours':{'label':'Office hours/student consultation', 
                    'help':'8. Office hours/student consultation'}, 
            'e_communication':{'label':'Electronic communication', 
                    'help':'9. Electronic communication'}, 
            'grading':{'label':'Grading **', 
                    'help':'10. Grading\u2020',
                    'extra':'\u2020Includes grading of all assignments, reports and examinations.'}, 
            'test_prep':{'label':'Quiz/exam preparation and invigilation', 
                    'help':'11. Quiz preparation/assist in exam preparation/Invigilation of exams'}, 
            'holiday':{'label':'Holiday compensation', 
                    'help':'12. Statutory Holiday Compensation\u2021',
                    'extra':'''\u2021To compensate for all statutory holidays which  
may occur in a semester, the total workload required will be reduced by %s
hour(s) for each base unit assigned excluding the additional %s B.U. for
preparation, e.g. %s hours reduction for %s B.U. appointment.''' % (HOLIDAY_HOURS_PER_BU, LAB_BONUS, 4.4, 4+LAB_BONUS)}}
    
    def __str__(self):
        return "TA: %s  Base Units: %s" % (self.member.person.userid, self.base_units)
    
    def save(self, newsitem=True, newsitem_author=None, *args, **kwargs):
        for f in self.config:
            # if 'weekly' in False is invalid, so we have to check if self.config[f] is iterable
            # before we check for 'weekly' or 'total'             
            if hasattr(self.config[f], '__iter__'):
                if 'weekly' in self.config[f]:
                    self.config[f]['weekly'] = _round_hours(self.config[f]['weekly'])
                if 'total' in self.config[f]:
                    self.config[f]['total'] = _round_hours(self.config[f]['total'])

        super(TUG, self).save(*args, **kwargs)
        if newsitem:
            n = NewsItem(user=self.member.person, author=newsitem_author, course=self.member.offering,
                    source_app='ta', title='%s Time Use Guideline Changed' % (self.member.offering.name()),
                    content='Your Time Use Guideline for %s has been changed. If you have not already, please review it with the instructor.' % (self.member.offering.name()),
                    url=self.get_absolute_url())
            n.save()

    def get_absolute_url(self):
        return reverse('offering:view_tug', kwargs={
                'course_slug': self.member.offering.slug, 
                'userid':self.member.person.userid})
    
    def max_hours(self):
        return self.base_units * HOURS_PER_BU

    def total_hours(self):
        """
        Total number of hours assigned
        """
        return round(sum((decimal.Decimal(data['total']) for _,data in self.iterfielditems() if data['total'])), 2)

class TAWorkloadReview(models.Model):
    """
    WR filled out by instructors
    
    Based on form in Appendix C (p. 73) of the collective agreement:
    http://www.tssu.ca/wp-content/uploads/2010/01/CA-2004-2010.pdf
    """	
    member = models.OneToOneField(Member, null=False, on_delete=models.PROTECT)    
    last_update = models.DateField(auto_now=True)
    reviewhour= models.BooleanField(help_text='Choose "yes" if further review is required.')
    reviewcomment = models.TextField(help_text='If No, explain briefly')
    reviewsignature = models.CharField(max_length=100, help_text="Instruction's Signature")
    reviewdate = models.DateField(help_text='Year/Month/Day')
    

    def save(self, newsitem=True, newsitem_author=None, *args, **kwargs):      
        super(TAWorkloadReview, self).save(*args, **kwargs)
        if newsitem:
            n = NewsItem(user=self.member.person, author=newsitem_author, course=self.member.offering,
                    source_app='ta', title='%s TA Workload Review Changed' % (self.member.offering.name()),
                    content='Your TA Workload Review for %s has been changed. If you have not already, please review it with the instructor.' % (self.member.offering.name()),
                    url=self.get_absolute_url())
            n.save()
        if self.reviewhour:
            self.send_notify()

    def get_absolute_url(self):
        return reverse('offering:view_ta_workload', kwargs={
                'course_slug': self.member.offering.slug, 
                'userid':self.member.person.userid})    

    def send_notify(self):
        subject = "Needs action: TA %s Workload Review for %s (%s) needs action." % (self.member.person.name(), self.member.offering.name(), self.member.offering.semester)
        content = "Needs action: TA %s Workload Review for %s (%s) needs action.\nFor more information, see %s" \
            % (self.member.person.name(), self.member.offering.name(),  self.member.offering.semester, settings.BASE_ABS_URL + self.get_absolute_url())
        
        to_email = []

        #/ta
        try:
            posting = TAPosting.objects.filter(semester=self.member.offering.semester, unit=self.member.offering.owner).first()
        except:
            posting = None
        if posting: 
            to_email.append(posting.contact().email())

        #/tacontracts
        try: 
            hiring_semester = HiringSemester.objects.filter(semester=self.member.offering.semester, unit=self.member.offering.owner).first()
        except: 
            hiring_semester = None
        if hiring_semester:
            to_email.append(hiring_semester.contact)

        if to_email:
            from_email = settings.DEFAULT_FROM_EMAIL
            msg = EmailMultiAlternatives(subject=subject, body=content, from_email=from_email,
                                        to=to_email, headers={'X-coursys-topic': 'ta'})        
            msg.send()

class TAEvaluation(models.Model):
    """
    TA Evaluation filled out by instructors with TA's comments
    
    """	
    # Section A
    member = models.OneToOneField(Member, null=False, on_delete=models.PROTECT)
    first_appoint = models.BooleanField(help_text="TA's First Appoint?", blank=True, null=True)
    draft = models.BooleanField(null=False, default=False)
    """ 
    Evaluation criteria
    Score - 1 meeting job requirements - good
            2 meeting job requirements - satisfactory
            3 does not meet job requirements - require more improvement
            4 does not meet job requirements - require major improvement
            N/A No opportunity to evaluate or criterion is not applicable

    """
    # Section B
    criteria_lab_prep = models.IntegerField(verbose_name='Preparation of Lab/Tutorial Material', blank=True, null=True)
    criteria_meet_deadline = models.IntegerField(verbose_name='Meets Deadlines', blank=True, null=True)
    criteria_maintain_hour = models.IntegerField(verbose_name='Maintains Office Hours', blank=True, null=True)
    criteria_attend_plan = models.IntegerField(verbose_name='Attendance at Planning/Coordinating Meetings', blank=True, null=True)
    criteria_attend_lec = models.IntegerField(verbose_name='Attendance at Lectures', blank=True, null=True)
    criteria_grading_fair = models.IntegerField(verbose_name='Grading Fair/Consistent', blank=True, null=True)
    criteria_lab_performance = models.IntegerField(verbose_name='Performance in Lab/Tutorial', blank=True, null=True)
    criteria_quality_of_feedback = models.IntegerField(verbose_name='Quality of Feedback', blank=True, null=True)
    criteria_quiz_prep = models.IntegerField(verbose_name='Quiz Preparation/Assist in Exam Preparation', blank=True, null=True)
    criteria_instr_content = models.IntegerField(verbose_name='Instructional Content', blank=True, null=True)
    criteria_others = models.IntegerField(verbose_name='Other Job Requirements', blank=True, null=True)
    criteria_other_comment = models.TextField(verbose_name='Comments', blank=True, null=True)
    # Section C
    positive_comment = models.TextField(verbose_name="Please comment on the TA's positive contributions to instruction (e.g. teaching methods, grading, ability to lead discussion) - or other noteworthy strengths", blank=True, null=True)
    improve_comment = models.TextField(verbose_name="Please comment on those duties which you noted as not meeting job requirements and suggest ways in which the TA's performance could be improved", blank=True, null=True)
    # Section D
    overall_evalation = models.BooleanField(verbose_name='Overall Meets Jobs Requirements', blank=True, null=True)
    recommend_TA = models.BooleanField(verbose_name='Would you recommend this TA for reappointment?', blank=True, null=True)
    no_recommend_comment = models.TextField(verbose_name='If No, explain briefly', blank=True, null=True)
    instructor_sign = models.CharField(verbose_name="Instruction's Signature", max_length=200)
    instructor_signdate = models.DateField(verbose_name='Evaluation Date', help_text='Year-Month-Day')
    # Section E
    ta_comment = models.TextField(verbose_name="TA's comment", blank=True, null=True)
    ta_sign = models.CharField(verbose_name="TA's Signature", blank=True, null=True, max_length=200)
    ta_signdate = models.DateField(verbose_name='TA Signed Date', help_text='Year-Month-Day', blank=True, null=True)
    
    last_update = models.DateField(auto_now=True)
    config = JSONField(null=False, blank=False, default=dict) # addition configuration stuff
    # 'released': indicate whether release sent to TA for TA comments
    # 'reminded': indicate whether reminder sent to TA for TA comments
    defaults = {'released': False, 'reminded': False}
    reminded, set_reminded = getter_setter('reminded')
    released, set_release = getter_setter('released')

    def is_past_nextsemstart(self):
        try:
            nextsemstart = self.member.offering.semester.next_semester().start               
            from datetime import date
            is_past_nextsemstart = date.today() >= nextsemstart
        except:
            is_past_nextsemstart = False
        return is_past_nextsemstart
    
    def is_past_nextsemend(self):
        try:
            nextsemend = self.member.offering.semester.next_semester().end            
            from datetime import date
            is_past_nextsemend = date.today() > nextsemend
        except:
            is_past_nextsemend = False
        return is_past_nextsemend
        
    @classmethod
    def send_reminders_for_draft_evals(cls):
        """
        Execute on day 0 of next term
        Get the list of TA Evals that was in draft and send reminders to the instructors
        """
        from log.models import LogEntry
        semester = Semester.current()
        released_semester = semester.previous_semester()        
        all_lastsem_draft = TAEvaluation.objects.filter(draft=True,  
                                                          member__offering__semester=released_semester, member__role="TA").select_related('member__person', 'member__offering')
        
        for drafteval in all_lastsem_draft:
            from_email = settings.DEFAULT_FROM_EMAIL

            # Send email notification to each instructor
            subject = 'You have a draft TA Evaluation for your TA %s. Please review and submit it.' % drafteval.member.person
            plaintext = get_template('ta/emails/notify_draft_ta_eval_for_instructor.txt')
            url = settings.BASE_ABS_URL + reverse('offering:edit_ta_evaluation_wizard', kwargs={'course_slug': drafteval.member.offering.slug, 'userid': drafteval.member.person.userid})
            email_context = {'person': drafteval.member.person, 'offering': drafteval.member.offering, 'url': url, 'instructor': drafteval.member.offering.instructors_str()}
    
            instructors = Member.objects.filter(role='INST', offering=drafteval.member.offering) 
            instructor_email_list = []   
            for member in instructors:
                instructor_email_list.append(member.person.email())    
            msg = EmailMultiAlternatives(subject=subject, body=plaintext.render(email_context),
                                         from_email=from_email, to=instructor_email_list, headers={'X-coursys-topic': 'ta'})
            msg.send()
            l = LogEntry(userid='sysadmin',
                         description=("automatically email notification to instructor %s for drafted Eval for %s %s") % (
                             drafteval.member.offering.instructors_str(), drafteval.member.offering, drafteval.member.person),
                         related_object=drafteval)
            l.save()
       
        return cls
    
    @classmethod
    def release_ta_evals(cls):
        """
        Execute on day 1 of next term
        Get the list of TA Evals that can be released so we can add a news item for the TA (and includes send them notification as well)
        """
        from log.models import LogEntry
        semester = Semester.current()
        released_semester = semester.previous_semester()        
        all_lastsem_taevals = TAEvaluation.objects.filter(draft=False, ta_signdate=None, 
                                                          member__offering__semester=released_semester, member__role="TA").select_related('member__person', 'member__offering')
        
        for taeval in all_lastsem_taevals:
            if not taeval.config.get('released'):
                from_email = settings.DEFAULT_FROM_EMAIL

                # create news item for each TA
                ta_edit_url = reverse('offering:edit_ta_evaluation_by_ta', kwargs={'course_slug': taeval.member.offering.slug, 'userid': taeval.member.person.userid})
                n = NewsItem(user=taeval.member.person, source_app="ta_evaluation", title="Your TA Evaluation Form is created. Please review and provide your comment.",
                    url=ta_edit_url, author=taeval.member.person, content="Your TA Evaluation Form is released. Please review and provide your comment.")
                n.save()
                
                # Send email notification to each TA (in case they turned off news notication)
                subject = 'Your TA Evaluation for %s is released. Please review and provide your comment.' % released_semester
                plaintext = get_template('ta/emails/notify_ta_eval_release_for_ta.txt')
                url = settings.BASE_ABS_URL + reverse('offering:edit_ta_evaluation_by_ta', kwargs={'course_slug': taeval.member.offering.slug, 'userid': taeval.member.person.userid})
                email_context = {'person': taeval.member.person, 'semester': released_semester, 'unit': taeval.member.offering.owner, 'url': url}

                to_email = taeval.member.person.email()        
                msg = EmailMultiAlternatives(subject=subject, body=plaintext.render(email_context),
                                    from_email=from_email, to=[to_email], headers={'X-coursys-topic': 'ta'})
                msg.send()
            
                taeval.config['released'] = True
                taeval.save()

                l = LogEntry(userid='sysadmin',
                            description=("automatically TA Eval Release to TA %s for %s") % (
                            taeval.member.person, released_semester),
                            related_object=taeval)
                l.save()
        return cls
    
    @classmethod
    def send_reminders_for_incomplete_evals(cls):
        """
        Execute on day 7, 14 of next term
        Get the list of incomplete TA Evals so we can add a news item for the TA (and includes send them notification as well)
        """
        from log.models import LogEntry
        semester = Semester.current()
        released_semester = semester.previous_semester()        
        all_lastsem_taevals = TAEvaluation.objects.filter(draft=False, ta_signdate=None, 
                                                          member__offering__semester=released_semester, member__role="TA").select_related('member__person', 'member__offering')
        
        for taeval in all_lastsem_taevals:
            from_email = settings.DEFAULT_FROM_EMAIL

            # Send email notification to each TA
            subject = 'You have not completed your part of the TA Evaluation for %s. Please review and provide your comment.' % released_semester
            plaintext = get_template('ta/emails/notify_tocomplete_ta_eval_for_ta.txt')
            url = settings.BASE_ABS_URL + reverse('offering:edit_ta_evaluation_by_ta', kwargs={'course_slug': taeval.member.offering.slug, 'userid': taeval.member.person.userid})
            email_context = {'person': taeval.member.person, 'semester': released_semester, 'unit': taeval.member.offering.owner, 'url': url}

            to_email = taeval.member.person.email()        
            msg = EmailMultiAlternatives(subject=subject, body=plaintext.render(email_context),
                                from_email=from_email, to=[to_email], headers={'X-coursys-topic': 'ta'})
            msg.send()
            taeval.config['reminded'] = True
            taeval.save()

            l = LogEntry(userid='sysadmin',
                        description=("automatically TA Eval Reminder to TA %s for %s") % (
                        taeval.member.person, released_semester),
                        related_object=taeval)
            l.save()            
        
        return cls
    
    @classmethod
    def send_incomplete_to_admin(cls):
        """
        On day 28 of next term
        Get the list of TA Evals that didn't have TA comments and send the PDF to admin
        """
        from log.models import LogEntry        
        semester = Semester.current()
        released_semester = semester.previous_semester()        
        all_lastsem_incomplete_taevals = TAEvaluation.objects.filter(draft=False, ta_signdate=None, 
                                                          member__offering__semester=released_semester, member__role="TA").select_related('member__person', 'member__offering')
        for taeval in all_lastsem_incomplete_taevals:
            to_email = []
            # get TA contact person
            # /ta
            try:
                posting = TAPosting.objects.filter(semester=released_semester, unit=taeval.member.offering.owner).first()
            except:
                posting = None
            if posting:
                to_email.append(posting.contact().email())
                
            #/tacontracts
            try: 
                hiring_semester = HiringSemester.objects.filter(semester=released_semester, unit=taeval.member.offering.owner).first()
            except: 
                hiring_semester = None
            if hiring_semester:
                to_email.append(hiring_semester.contact)

            if to_email:
                subject = 'An incompleted TA Evaluation Form for TA %s (%s) was sent to you for filing' % (taeval.member.person.name(), taeval.member.offering.semester)    
                plaintext = get_template('ta/emails/notify_incomplete_ta_eval_for_admin.txt')
                url = settings.BASE_ABS_URL + reverse('offering:view_ta_evaluation', kwargs={'course_slug': taeval.member.offering.slug, 'userid': taeval.member.person.userid})
                email_context = {'person': taeval.member.person, 'posting': taeval.member.offering, 'url': url, 'status': 'an incompleted'}
                    
                response = HttpResponse(content_type="application/pdf")   
                ta_evaluation_form(taeval, taeval.member, taeval.member.offering, response)
                    
                from_email = settings.DEFAULT_FROM_EMAIL
                msg = EmailMultiAlternatives(subject=subject, body=plaintext.render(email_context),
                            from_email=from_email, to=to_email, headers={'X-coursys-topic': 'ta'})
                msg.attach(('%s-%s.pdf' % (taeval.member.person.emplid, datetime.datetime.now().strftime('%Y%m%dT%H%M%S'))), response.getvalue(),
                            'application/pdf')
                msg.send()  

                l = LogEntry(userid='sysadmin',
                        description=("automatically sending incomplete TA Eval for %s on %s") % (
                        taeval.member.person, released_semester.name),
                        related_object=taeval)
                l.save()      

        return cls
    
CATEGORY_CHOICES = ( # order must match list in TAPosting.config['salary']
        ('GTA1', 'Masters'),
        ('GTA2', 'PhD'),
        ('UTA', 'Undergrad'),
        ('ETA', 'External'),
)

class TAPosting(models.Model):
    """
    Posting for one unit in one semester
    """
    semester = models.ForeignKey(Semester, on_delete=models.PROTECT)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    opens = models.DateField(help_text='Opening date for the posting')
    closes = models.DateField(help_text='Closing date for the posting')
    def autoslug(self):
        return make_slug(self.semester.slugform() + "-" + self.unit.label)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)
    config = JSONField(null=False, blank=False, default=dict) # addition configuration stuff:
        # 'salary': default pay rates per BU for each GTA1, GTA2, UTA, EXT: ['1.00', '2.00', '3.00', '4.00']
        # 'scholarship': default scholarship rates per BU for each GTA1, GTA2, UTA, EXT
        # 'accounts': default accounts for GTA1, GTA2, UTA, EXT (ra.models.Account.id values)
        # 'start': default start date for contracts ('YYYY-MM-DD')
        # 'end': default end date for contracts ('YYYY-MM-DD')
        # 'payroll_start': default payroll start date for contracts ('YYYY-MM-DD')
        # 'payroll_end': default payroll start date for contracts ('YYYY-MM-DD')
        # 'deadline': default deadline to accept contracts ('YYYY-MM-DD')
        # 'excluded': courses to exclude from posting (list of Course.id values)
        # 'payperiods': number of pay periods in the semeseter
        # 'contact': contact person for offer questions (Person.id value)
        # 'max_courses': Maximum number of courses an applicant can select
        # 'min_courses': Minimum number of courses an applicant can select
        # 'offer_text': Text to be displayed when students accept/reject the offer (creole markup)
        # 'export_seq': sequence ID for payroll export (so we can create a unique Batch ID)
        # 'extra_questions': additional questions to ask applicants
        # 'instructions': instructions for completing the TA Application
        # 'hide_campuses': whether or not to prompt for Campus
        # 'send_notify': send email notification to contact person when someone accepts or declines an offer (default True)
        # 'tssu_link': URL showing on TUG for TSSU collective agreement

    defaults = {
            'salary': ['0.00']*len(CATEGORY_CHOICES),
            'scholarship': ['0.00']*len(CATEGORY_CHOICES),
            'accounts': [None]*len(CATEGORY_CHOICES),
            'start': '',
            'end': '',
            'payroll_start': '',
            'payroll_end': '',
            'deadline': '',
            'excluded': [],
            'bu_defaults': {},
            'payperiods': 8,
            'max_courses': 10,
            'min_courses': 0,
            'contact': None,
            'offer_text': '',
            'export_seq': 0,
            'extra_questions': [],
            'instructions': '',
            'hide_campuses': False,            
            'send_notify': True,
            'tssu_link': 'https://www.sfu.ca/human-resources/tssu.html'
            }
    salary, set_salary = getter_setter('salary')
    scholarship, set_scholarship = getter_setter('scholarship')
    accounts, set_accounts = getter_setter('accounts')
    start, set_start = getter_setter('start')
    end, set_end = getter_setter('end')
    payroll_start, set_payroll_start = getter_setter('payroll_start')
    payroll_end, set_payroll_end = getter_setter('payroll_end')
    deadline, set_deadline = getter_setter('deadline')
    excluded, set_excluded = getter_setter('excluded')
    bu_defaults, set_bu_defaults = getter_setter('bu_defaults')
    payperiods_str, set_payperiods = getter_setter('payperiods')
    max_courses, set_max_courses = getter_setter('max_courses')
    min_courses, set_min_courses = getter_setter('min_courses')
    offer_text, set_offer_text = getter_setter('offer_text')
    extra_questions, set_extra_questions = getter_setter('extra_questions')
    instructions, set_instructions = getter_setter('instructions')
    hide_campuses, set_hide_campuses = getter_setter('hide_campuses')
    send_notify, set_send_notify = getter_setter('send_notify')
    tssu_link, set_tssu_link = getter_setter('tssu_link')    
    _, set_contact = getter_setter('contact')
    
    class Meta:
        unique_together = (('unit', 'semester'),)
    def __str__(self): 
        return "%s, %s" % (self.unit.name, self.semester)
    def save(self, *args, **kwargs):
        super(TAPosting, self).save(*args, **kwargs)
        key = self.html_cache_key()
        cache.delete(key)

    def short_str(self):
        return "%s %s" % (self.unit.label, self.semester)
    def delete(self, *args, **kwargs):
        raise NotImplementedError("This object cannot be deleted because it is used as a foreign key.")
    
    def contact(self):
        if 'contact' in self.config:
            return Person.objects.get(id=self.config['contact'])
        else:
            return None
    def payperiods(self):
        return decimal.Decimal(self.payperiods_str())
    
    def selectable_courses(self):
        """
        Course objects that can be selected as possible choices
        """
        excl = set(self.excluded())
        offerings = CourseOffering.objects.filter(semester=self.semester, owner=self.unit).select_related('course')
        # remove duplicates and sort nicely
        courses = list(set((o.course for o in offerings if o.course_id not in excl)))
        courses.sort()
        return courses
    
    def selectable_offerings(self):
        """
        CourseOffering objects that can be selected as possible choices
        """
        excl = set(self.excluded())
        offerings = CourseOffering.objects.filter(semester=self.semester, owner=self.unit).exclude(course__id__in=excl)
        return offerings
    
    def is_open(self):
        today = datetime.date.today()
        return self.opens <= today <= self.closes
    
    def next_export_seq(self):
        if 'export_seq' in self.config:
            current = self.config['export_seq']
        else:
            current = 0
        
        self.config['export_seq'] = current + 1
        self.save()
        return self.config['export_seq']
    
    def cat_index(self, val):
        indexer = dict((v[0],k) for k,v in enumerate(CATEGORY_CHOICES))
        return indexer.get(val)
    
    def default_bu(self, offering, count=None):
        """
        Default BUs to assign for this course offering
        """
        strategy = bu_rules.get_bu_strategy( self.semester, self.unit )
        return strategy( self, offering, count )

    def required_bu(self, offering, count=None):
        if self.unit.label in ["CMPT", "COMP"] and self.semester.name >= "1231":
            """
            new calculation for CMPT BU
            CMPT_WCOURSE_BU = 2
            CMPT_COURSE_BU = 1
            LAB_BONUS_DECIMAL = 0.17 = Prep BU
            W course: default + extra + 2 + ((1 + 0.17) * TA)
            all course: default + extra + ((1 + 0.17) * TA)
            labs: no additional BU given since all TA will get 0.17
            """
            default = self.default_bu(offering, count=count)
            extra = offering.extra_bu()        
            tacourses = TACourse.objects.filter(contract__posting=self, course=offering).exclude(contract__status__in=['REJ', 'CAN'])
            if offering.flags.write:
                return default + extra + CMPT_WCOURSE_BU + decimal.Decimal((CMPT_COURSE_BU + LAB_BONUS_DECIMAL) * len(tacourses)) 
            else:                
                return default + extra + decimal.Decimal((CMPT_COURSE_BU + LAB_BONUS_DECIMAL)* len(tacourses)) 
        else:
            """
                Actual BUs to assign to this course: default + extra + 0.17*number of TA's
            """
            default = self.default_bu(offering, count=count)
            extra = offering.extra_bu()

            if offering.labtas():
                tacourses = TACourse.objects.filter(contract__posting=self, course=offering).exclude(contract__status__in=['REJ', 'CAN'])
                return default + extra + decimal.Decimal(LAB_BONUS_DECIMAL * len(tacourses)) 
            else:
                return default + extra

    def required_bu_cap(self, offering):
        if self.unit.label in ["CMPT", "COMP"] and self.semester.name >= "1231":
            """
            Call required_bu function with enrl_cap
            """
            return self.required_bu(self, offering, offering.enrl_cap)
        else:
            """
            Actual BUs to assign to this course at its enrolment cap
            """
            default = self.default_bu(offering, offering.enrl_cap)
            extra = offering.extra_bu()
            return default + extra

    def assigned_bu(self, offering):
        """
        BUs already assigned to this course
        """
        total = decimal.Decimal(0)
        tacourses = TACourse.objects.filter(contract__posting=self, course=offering).exclude(contract__status__in=['REJ', 'CAN']).select_related('course__semester', 'contract__posting__unit')
        if(tacourses.count() > 0):
            total = sum([t.total_bu for t in tacourses])
        return decimal.Decimal(total)

    def applicant_count(self, offering):
        """
        Number of people who have applied to TA this offering
        """
        prefs = CoursePreference.objects.filter(app__posting=self, app__late=False, course=offering.course).exclude(rank=0)
        return prefs.count()
    
    def ta_count(self, offering):
        """
        Number of people who have assigned to be TA for this offering
        """
        tacourses = TACourse.objects.filter(contract__posting=self, course=offering).exclude(contract__status__in=['REJ', 'CAN'])
        return tacourses.count()
    
    def total_pay(self, offering):
        """
        Payments for all tacourses associated with this offering 
        """
        total = 0
        tacourses = TACourse.objects.filter(course=offering, contract__posting=self).exclude(contract__status__in=['REJ', 'CAN'])
        for course in tacourses:
            total += course.pay()
        return total
    
    def all_total(self):
        """
        BU's and Payments for all tacourses associated with all offerings 
        """
        pay = 0
        bus = 0
        tac = TAContract.objects.filter(posting=self).exclude(status__in=['REJ', 'CAN']).count()
        tacourses = TACourse.objects.filter(contract__posting=self).exclude(contract__status__in=['REJ', 'CAN'])
        for course in tacourses:
            pay += course.pay()
            bus += course.total_bu
        return (bus, pay, tac)
    
    def html_cache_key(self):
        return "taposting-offertext-html-" + str(self.id)
    def html_offer_text(self):
        """
        Return the HTML version of this offer's offer_text
        
        Cached to save frequent conversion.
        """
        key = self.html_cache_key()
        html = cache.get(key)
        if html:
            return mark_safe(html)
        else:
            html = markup_to_html(self.offer_text(), 'creole')
            cache.set(key, html, 24*3600) # expires on self.save() above
            return html
    
        
class Skill(models.Model):
    """
    Skills an applicant specifies in their application.  Skills are specific to a posting.
    """
    posting = models.ForeignKey(TAPosting, on_delete=models.PROTECT)
    name = models.CharField(max_length=30)
    position = models.IntegerField()
    
    class Meta:
        ordering = ['position']
        unique_together = (('posting', 'position'))
    def __str__(self):
        return "%s in %s" % (self.name, self.posting)


def _file_upload_to(instance, filename):
    """
    path to upload TA Application resume
    """
    return upload_path('ta_applications', filename)


_resume_upload_to = _file_upload_to
_transcript_upload_to = _file_upload_to

class TAApplication(models.Model):
    """
    TA application filled out by students
    """
    VALIDSIN_CHOICES = (
        ('Yes', 'Yes'),
        ('No', 'No'),
    )

    posting = models.ForeignKey(TAPosting, on_delete=models.PROTECT)
    person = models.ForeignKey(Person, on_delete=models.PROTECT)
    category = models.CharField(max_length=4, blank=False, null=False, choices=CATEGORY_CHOICES, verbose_name='Category', help_text='What category of program are you currently studying?')
    current_program = models.CharField(max_length=100, blank=True, null=True, verbose_name="Current program", choices=DEPT_CHOICES,
        help_text='In what department are you currently a student?')
    program_comment = models.CharField(max_length=100, verbose_name='Other program comment', null=True, blank=True, help_text='If you select "Other program" in Department, please indicate which programs did you study.')
    supervisor = models.ForeignKey(Person, blank=True, related_name='tasupervisor', null=True, verbose_name="If you are CS grad student, please identify your supervisor", on_delete=models.PROTECT)
    sin = models.CharField(blank=True, max_length=30, verbose_name="SIN",help_text="Social insurance number (required for receiving payments)")
    validsin = models.CharField(choices=VALIDSIN_CHOICES, max_length=3, verbose_name="SIN",help_text='Do you have valid SIN at the time of employment?')
    base_units = models.DecimalField(max_digits=4, decimal_places=2, default=5,
            help_text='Maximum number of base units (BU\'s) you would accept. Each BU represents a maximum of 42 hours of work for the semester. TA appointments can consist of 2 to 5 base units and are based on course enrollments and department requirements.')
    experience =  models.TextField(blank=True, null=True,
        verbose_name="Additional Experience",
        help_text='Describe any other experience that you think may be relevant to these courses.')
    course_load = models.TextField(blank=True, verbose_name="Intended course load",
        help_text='Describe the intended course load of the semester being applied for.')
    other_support = models.TextField(blank=True, null=True,
        verbose_name="Other financial support",
        help_text='Do you have a merit based scholarship or fellowship (e.g. FAS Graduate Fellowship) in the semester that you are applying for? ')
    comments = models.TextField(verbose_name="Additional comments", blank=True, null=True)
    preference_comment = models.TextField(verbose_name='Course preference comment', null=True, blank=True, help_text='If you are applying for a course with multiple sections, please indicate which section you prefer.')
    rank = models.IntegerField(blank=False, default=0)
    late = models.BooleanField(blank=False, default=False)
    resume = models.FileField("Curriculum Vitae (CV)", storage=UploadedFileStorage, upload_to=_resume_upload_to, max_length=500,
                              blank=True, null=True, help_text='Please attach your Curriculum Vitae (CV).')
    resume_mediatype = models.CharField(max_length=200, null=True, blank=True, editable=False)
    transcript = models.FileField(storage=UploadedFileStorage, upload_to=_transcript_upload_to, max_length=500, blank=True,
                                  null=True, help_text='Please attach your unofficial transcript.')
    transcript_mediatype = models.CharField(max_length=200, null=True, blank=True, editable=False)
    admin_created = models.BooleanField(blank=False, default=False)
    new_workers_training = models.BooleanField('I have completed the SFU Safety Orientation training',
                                               default=False,
                                               help_text=mark_safe('Have you completed the University\'s safety '
                                                         'orientation? SFU has a <a href="https://canvas.sfu.ca/enroll/RR8WDW">short online module</a> you can take online'
                                                         'and periodically '
                                                         'offers classroom sessions of the same material.  Some '
                                                         'research and instructional laboratories may require '
                                                         'additional training, contact the faculty member in charge of '
                                                         'your lab(s) for details.'))
    config = JSONField(null=False, blank=False, default=dict)
        # 'extra_questions' - a dictionary of answers to extra questions. {'How do you feel?': 'Pretty sharp.'} 
 
    class Meta:
        unique_together = (('person', 'posting'),)
    def __str__(self):
        return "%s  Posting: %s" % (self.person, self.posting)
    
    def course_pref_display(self):
        crs = []
        cps = self.coursepreference_set.exclude(rank=0).order_by('rank').select_related('course')
        for cp in cps:
            crs.append(cp.course.subject + ' ' + cp.course.number)
        return ', '.join(crs)
    
    def course_assigned_display(self):
        crs = []
        tacrss = TACourse.objects.filter(contract__application=self).exclude(contract__status__in=['CAN', 'REJ'])\
            .select_related('course')
        for tacrs in tacrss:
            crs.append(tacrs.course.subject + ' ' + tacrs.course.number)
        return ', '.join(crs)
    
    def base_units_assigned(self):
        crs = TACourse.objects.filter(contract__application=self).exclude(contract__status__in=['CAN', 'REJ'])\
            .aggregate(Sum('bu'))
        return crs['bu__sum']

    def campus_pref_display(self):
        cmp = []
        prefs = self.campuspreference_set.all()
        for p in prefs:
              if p.pref == 'PRF':
                cmp.append(p.get_campus_display())
        return ', '.join(cmp)

    def email_application(self):
            plaintext = get_template('ta/emails/notify_application.txt')
            html = get_template('ta/emails/notify_application.html')

            email_context = {'person': self.person, 'posting': self.posting}
            subject = 'Thank you for applying TA position (%s) ' % (self.posting.semester)
            if self.posting.contact():
                from_email = self.posting.contact().email()
            else:
                from_email = settings.DEFAULT_FROM_EMAIL
            to = self.person.email()

            msg = EmailMultiAlternatives(subject=subject, body=plaintext.render(email_context),
                    from_email=from_email, to=[to], headers={'X-coursys-topic': 'ta'})
            msg.attach_alternative(html.render(email_context), "text/html")
            msg.send()

    def coursys_supervisor_display(self):
        supervisor = ''
        gradids = GradStudent.objects.filter(person_id=self.person_id, current_status='ACTI').values_list('id', flat=True)
        supers = Supervisor.objects.filter(student_id__in=gradids).all().select_related('supervisor')
        for s in supers:
            if s.supervisor is not None:
                supervisor += s.supervisor.name_pref() + ' ('+ str(s.supervisor_type) + '), '
        return supervisor[:-2]

    def grad_program_information(self):
        active_gs = GradStudent.objects.filter(person=self.person, current_status__in=STATUS_REAL_PROGRAM) \
                .select_related('program__unit')
        gradprogram = []
        for st in active_gs:
            gradprogram.append(st.program.label)
        return ', '.join(gradprogram)

    def contract_status_display(self):
        status = ''
        tacontract = self.tacontract_set.first()
        if tacontract is not None:
            status = tacontract.get_status_display() + ': '+ str(tacontract.bu())
        return status

    def skill_level_display(self):
        skill = []
        taskill = SkillLevel.objects.filter(app=self)
        for s in taskill:
            if s is not None and s.get_level_display() != 'None':
                skill.append(s.skill.name + ': '+ s.get_level_display())
        return ', '.join(skill)

    def past_experience_display(self):
        pastexp = []
        previous_experience = TACourse.objects.filter(contract__application__person=self.person) \
                    .exclude(contract__application=self).select_related('course__semester')
        for p in previous_experience:
            if p.course.name is not None and p.bu > 0:
                pastexp.append(p.course.subject + ' ' + p.course.number + ' ' + p.course.section)
        return ', '.join(pastexp)

    def past_enroll_display(self):
        member = []
        membership = Member.objects.filter(person=self.person, role='STUD', offering__semester__end__lte=datetime.date.today()).select_related('offering')
        for m in membership:
            if m.offering.name is not None :
                member.append(m.offering.subject + ' ' + m.offering.number + ' ' + m.offering.section)
        return ', '.join(member)
        
PREFERENCE_CHOICES = (
        ('PRF', 'Preferred'),
        ('NOP', 'No Preference'),
        #('WIL', 'Willing'),
        #('NOT', 'Not willing'),
)
PREFERENCES = dict(PREFERENCE_CHOICES)

class CampusPreference(models.Model):
    """
    Preference ranking for a campuses
    """
    app = models.ForeignKey(TAApplication, on_delete=models.PROTECT)
    campus = models.CharField(max_length=5, choices=CAMPUS_CHOICES)
    pref = models.CharField(max_length=3, choices=PREFERENCE_CHOICES)
    class Meta:
        unique_together = (('app', 'campus'),)

LEVEL_CHOICES = (
    ('EXPR', 'Expert'),
    ('GOOD', 'Good'),
    ('SOME', 'Some'),
    ('NONE', 'None'),
)
LEVELS = dict(LEVEL_CHOICES)
class SkillLevel(models.Model):
    """
    Skill of an applicant
    """
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT)
    app = models.ForeignKey(TAApplication, on_delete=models.PROTECT)
    level = models.CharField(max_length=4, choices=LEVEL_CHOICES)
    #class Meta:
    #    unique_together = (('app', 'skill'),)


APPOINTMENT_CHOICES = (
        ("INIT","Initial appointment to this position"),
        ("REAP","Reappointment to same position or revision to appointment"),       
    )
STATUS_CHOICES = (
        ("NEW","Draft"), # not yet sent to TA
        ("OPN","Offered"), # offer made, but not accepted/rejected/cancelled
        ("REJ","Rejected"), 
        ("ACC","Accepted"),
        ("SGN","Contract Signed"), # after accepted and manager has signed contract
        ("CAN","Cancelled"),
    )
STATUS = dict(STATUS_CHOICES)
STATUSES_NOT_TAING = ['NEW', 'REJ', 'CAN'] # statuses that mean "not actually TAing"

DEFAULT_EMAIL_TEXT = "Please find attached a copy of your TA contract."
DEFAULT_EMAIL_SUBJECT = "Your TA contract."


class TAContract(models.Model):
    """    
    TA Contract, filled in by TAAD
    """
    status  = models.CharField(max_length=3, choices=STATUS_CHOICES, verbose_name="Appointment Status", default="NEW")
    posting = models.ForeignKey(TAPosting, on_delete=models.PROTECT)
    application = models.ForeignKey(TAApplication, on_delete=models.PROTECT)
    sin = models.CharField(max_length=30, verbose_name="SIN",help_text="Social insurance number")
    appointment_start = models.DateField(null=True, blank=True)
    appointment_end = models.DateField(null=True, blank=True)
    pay_start = models.DateField()
    pay_end = models.DateField()
    appt_category = models.CharField(max_length=4, choices=CATEGORY_CHOICES, verbose_name="Appointment Category", default="GTA1")
    position_number = models.ForeignKey(Account, on_delete=models.PROTECT)
    appt = models.CharField(max_length=4, choices=APPOINTMENT_CHOICES, verbose_name="Appointment", default="INIT")
    pay_per_bu = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Pay per Base Unit Semester Rate.",)
    scholarship_per_bu = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Scholarship per Base Unit Semester Rate.",)
    appt_cond = models.BooleanField(default=False, verbose_name="Conditional")
    appt_tssu = models.BooleanField(default=True, verbose_name="Appointment in TSSU")
    deadline = models.DateField(verbose_name="Acceptance Deadline", help_text='Deadline for the applicant to accept/decline the offer')
    remarks = models.TextField(blank=True)
    
    created_by = models.CharField(max_length=8, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    config = JSONField(default=dict)
    # 'accepted_date': last accept date for contract ('YYYY-MM-DD')
    # 'rejected_date': last rejected date for contract ('YYYY-MM-DD')

    class Meta:
        unique_together = (('posting', 'application'),)
        
    def __str__(self):
        return "%s" % self.application.person

    def save(self, *args, **kwargs):
        super(TAContract, self).save(*args, **kwargs)

        # set SIN field on any GradStudent objects for this person
        from grad.models import GradStudent
        for gs in GradStudent.objects.filter(person=self.application.person):
            dummy_sins = ['999999999', '000000000', '123456789']
            if (('sin' not in gs.config 
                or ('sin' in gs.config and gs.config['sin'] in dummy_sins)) 
                and not self.sin in dummy_sins ):
                gs.person.set_sin(self.sin)
                gs.person.save()

        from tacontracts.models import TAContract as NewTAContract
        NewTAContract.update_ta_members(self.application.person, self.posting.semester_id)

        # If the status of this contract is Cancelled or Rejected, find all the TACourses
        # it applies to and set their BUs to 0.
        if self.status in ('CAN', 'REJ'):
            courses = TACourse.objects.filter(contract=self)
            for course in courses:
                course.bu = 0
                course.save()

    def first_assign(self, application, posting):
        self.application = application
        self.posting = posting
        self.sin = application.sin
        self.appt_category = application.category
        self.appointment_start = posting.start()
        self.appointment_end = posting.end()
        # New postings may have proper payroll_start/end fields.  If so, let's use them,
        # otherwise, use the same fields as for the appointment start/end for backwards compatibility.
        if posting.payroll_start():
            self.pay_start = posting.payroll_start()
        else:
            self.pay_start = posting.start()
        if posting.payroll_end():
            self.pay_end = posting.payroll_end()
        else:
            self.pay_end = posting.end()
        self.deadline = posting.deadline()
        index = posting.cat_index(application.category)
        self.position_number = Account.objects.get(pk=posting.accounts()[index])
        self.pay_per_bu = posting.salary()[index]
        self.scholarship_per_bu = posting.scholarship()[index]
        self.save()

    def bu(self):
        courses = self.tacourse_set.all()
        if self.status in ('CAN', 'REJ'):
            return 0
        return sum([course.bu for course in courses])

    def total_bu(self):
        courses = TACourse.objects.filter(contract=self)
        if self.status in ('CAN', 'REJ'):
            return 0
        return sum([course.total_bu for course in courses])

    def prep_bu(self):
        courses = TACourse.objects.filter(contract=self)
        if self.status in ('CAN', 'REJ'):
            return 0
        return sum([course.prep_bu for course in courses])

    def total_pay(self):
        return decimal.Decimal(self.bu()) * self.pay_per_bu

    def scholarship_pay(self):
        return decimal.Decimal(self.bu()) * self.scholarship_per_bu

    @property
    def should_be_added_to_the_course(self):
        return self.status in ['SGN', 'ACC']

    @property
    def total(self):
        return self.total_pay() + self.scholarship_pay()

    def course_list_string(self):
        # Build a string of all course offerings tied to this contract for CSV downloads and grad student views.
        course_list_string = ', '.join(ta_course.course.name() for ta_course in self.tacourse_set.all())
        return course_list_string

    def email_contract(self):
        unit = self.posting.unit
        try:
            contract_email = unit.contract_email_text
            content = contract_email.content
            subject = contract_email.subject
        except TAContractEmailText.DoesNotExist:
            content = DEFAULT_EMAIL_TEXT
            subject = DEFAULT_EMAIL_SUBJECT

        response = HttpResponse(content_type="application/pdf")
        response['Content-Disposition'] = 'inline; filename="%s-%s.pdf"' % (self.posting.slug,
                                                                            self.application.person.userid)
        ta_form(self, response)
        to_email = self.application.person.email()
        if self.posting.contact():
            from_email = self.posting.contact().email()
        else:
            from_email = settings.DEFAULT_FROM_EMAIL
        msg = EmailMultiAlternatives(subject, content, from_email,
                                     [to_email], headers={'X-coursys-topic': 'ta'})
        msg.attach(('"%s-%s.pdf' % (self.posting.slug, self.application.person.userid)), response.getvalue(),
                   'application/pdf')
        msg.send()

    def send_notify(self, status):
        subject = 'TA %s has %s the TA offer for %s' % (self.application.person.name(), status, self.posting.semester)
        content = 'TA %s has %s the TA offer for %s' % (self.application.person.name(), status, self.posting.semester)
        
        to_email = self.posting.contact().email()
        from_email = settings.DEFAULT_FROM_EMAIL
        msg = EmailMultiAlternatives(subject=subject, body=content, from_email=from_email,
                                     to=[to_email], headers={'X-coursys-topic': 'ta'})        
        msg.send()


class CourseDescription(models.Model):
    """
    Description of the work for a TA contract
    """
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    description = models.CharField(max_length=60, blank=False, null=False, help_text="Description of the work for a course, as it will appear on the contract. (e.g. 'Office/marking')")
    labtut = models.BooleanField(default=False, verbose_name="Lab/Tutorial?", help_text="Does this description get the %s BU bonus?"%(LAB_BONUS))
    hidden = models.BooleanField(default=False)
    config = JSONField(null=False, blank=False, default=dict)
    
    def __str__(self):
        return self.description

    def delete(self):
        """Like most of our objects, we don't want to ever really delete it."""
        self.hidden = True
        self.save()


class TACourse(models.Model):
    course = models.ForeignKey(CourseOffering, blank=False, null=False, on_delete=models.PROTECT)
    contract = models.ForeignKey(TAContract, blank=False, null=False, on_delete=models.PROTECT)
    description = models.ForeignKey(CourseDescription, blank=False, null=False, on_delete=models.PROTECT)
    bu = models.DecimalField(max_digits=4, decimal_places=2)
    
    class Meta:
        unique_together = (('contract', 'course'),)
    
    def __str__(self):
        return "Course: %s  TA: %s" % (self.course, self.contract)

    @property
    def prep_bu(self):
        """
        Return the prep BUs for this assignment
        """
        if self.contract.posting.unit.label in ["CMPT", "COMP"] and self.course.semester.name >= "1234":                           
            return LAB_BONUS_DECIMAL
        else:
            if self.has_labtut():
                # If the contract that is attached to this course has been cancelled/rejected, there
                # really aren't any BUs that are really used here.
                if self.contract.status in ('CAN', 'REJ'):
                    return 0
                else:
                    return LAB_BONUS_DECIMAL
            else:
                return 0

    @property
    def total_bu(self):
        """
        Return the total BUs for this assignment
        """
        # If the contract that is attached to this course has been cancelled/rejected, there
        # really aren't any BUs that are really used here.
        if self.contract.status in ('CAN', 'REJ'):
                return 0
        else:
            return self.bu + self.prep_bu

    @property
    def hours(self):
        return self.bu * HOURS_PER_BU

    @property
    def hours_per_bu(self):
        return HOURS_PER_BU

    @property
    def holiday_hours_per_bu(self):
        return HOLIDAY_HOURS_PER_BU

    @property
    def holiday_hours(self):
        return self.bu * HOLIDAY_HOURS_PER_BU

    @property
    def min_tug_prep(self):
        """
        The fewest hours the instructor should be able to assign for "prep" in the TUG.

        Courses with labs/tutorials must used 1 BU for prep. In addition to the 0.17 BU that must be used for prep.
        That's a *totally* different kind of prep.
        """
        return HOURS_PER_BU if self.has_labtut() else 0

    def has_labtut(self):
        """
        Does this assignment deserve the LAB_BONUS bonus?
        """
        return self.description.labtut
    
    def default_description(self):
        """
        Guess an appropriate CourseDescription object for this contract. Must have self.course filled in first.
        """
        labta = self.course.labtas()
        descs = CourseDescription.objects.filter(unit=self.contract.posting.unit, hidden=False, labtut=labta)
        if descs:
            return descs[0]
        else:
            raise ValueError("No appropriate CourseDescription found")
    
    def pay(self):
        contract = self.contract
        if contract.status in STATUSES_NOT_TAING:
            return decimal.Decimal(0)
        total = self.total_bu * contract.pay_per_bu
        total += self.bu * contract.scholarship_per_bu
        return total
        
TAKEN_CHOICES = (
        ('YES', 'Yes: this course at SFU'),
        ('SIM', 'Yes: a similar course elsewhere'),
        ('KNO', 'No, but I know the course material'),
        ('NO', 'No, I don\'t know the material well'),
        )
EXPER_CHOICES = (
        ('FAM', 'Very familiar with course material'),
        ('SOM', 'Somewhat familiar with course material'),
        ('NOT', 'Not familiar with course material'),
        )
    
class CoursePreference(models.Model):
    app = models.ForeignKey(TAApplication, on_delete=models.PROTECT)
    course = models.ForeignKey(Course, on_delete=models.PROTECT)
    taken = models.CharField(max_length=3, choices=TAKEN_CHOICES, blank=True, null=True)
    exper = models.CharField(max_length=3, choices=EXPER_CHOICES, blank=True, null=True, verbose_name="Experience")
    rank = models.IntegerField(blank=False)
    #class Meta:
    #    unique_together = (('app', 'course'),)

    def __str__(self):
        if self.app_id and self.course_id:
            return "%s's pref for %s" % (self.app.person, self.course)
        else:
            return "new CoursePreference"


# An object to store the content that will be emailed when the contract automatically gets emailed upon the TA
# accepting.  There should be only one of these per unit, so that it's only set once per school.  Realistically, only
# CMPT uses this.
class TAContractEmailText(models.Model):
    unit = models.OneToOneField(Unit, editable=False, on_delete=models.PROTECT, related_name='contract_email_text')
    subject = models.CharField(max_length=250, help_text='e.g. "Your TA Contract"')
    content = models.TextField(help_text='e.g. "Please find enclosed your TA Contract..."')

    def __str__(self):
        return "TA contract acceptance text for %s" % self.unit.label.upper()
