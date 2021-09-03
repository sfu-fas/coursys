from django import forms
from grades.models import ACTIVITY_STATUS_CHOICES, NumericActivity, LetterActivity, CalNumericActivity, Activity, NumericGrade, LetterGrade,ACTIVITY_TYPES, LETTER_GRADE_CHOICES
from coredata.models import CourseOffering
from groups.models import GroupMember
from django.utils.safestring import mark_safe
import pickle
import datetime
from grades.utils import parse_and_validate_formula, ValidationError
from submission.models import Submission
from dashboard.models import NewsItem
from courselib.markup import MarkupContentField, MarkupContentMixin


FORMTYPE = {'add': 'add', 'edit': 'edit'}
GROUP_STATUS_CHOICES = [
    ('0', 'Yes'),
    ('1', 'No') ]
GROUP_STATUS = dict(GROUP_STATUS_CHOICES)
GROUP_STATUS_MAP = {'0': True, '1': False}


class ActivityForm(forms.Form):
    name = forms.CharField(max_length=30,
                    help_text='Name of the activity, e.g "Assignment 1" or "Midterm"',
                    widget=forms.TextInput(attrs={'size':'30'}))
    short_name = forms.CharField(max_length=15,
                                help_text='Short version of the name for column headings, e.g. "A1" or "MT"',
                                widget=forms.TextInput(attrs={'size':'8'}))
    percent = forms.DecimalField(max_digits=5, decimal_places=2, required=False, label='Percentage',
                                 help_text='Percent of final mark',
                                 widget=forms.NumberInput(attrs={'class': 'smallnumberinput'}))
    url = forms.URLField(required=False, label='URL',
                                 help_text='Page for more information, e.g. assignment description or exam info',
                                 widget=forms.TextInput(attrs={'size':'60'}))

    def __init__(self, *args, **kwargs):
        super(ActivityForm, self).__init__(*args, **kwargs)
        self._addform_validate = False
        self._editform_validate = False

    def activate_addform_validation(self, course_slug):
        self._addform_validate = True
        self._course_slug = course_slug
        
    def activate_editform_validation(self, course_slug, activity_slug):
        self._editform_validate = True
        self._course_slug = course_slug
        self._activity_slug = activity_slug
        
    def clean_name(self):
        name = self.cleaned_data['name']
        if name:
            if self._addform_validate:
                if Activity.objects.filter(offering__slug=self._course_slug, name=name).count() > 0:
                    raise forms.ValidationError('Activity with the same name already exists')
            if self._editform_validate:
                if Activity.objects.filter(offering__slug=self._course_slug, name=name).exclude(slug=self._activity_slug).count() > 0:
                    raise forms.ValidationError('Activity with the same name already exists')
        
        return name
    
    def clean_short_name(self):
        short_name = self.cleaned_data['short_name']
        if short_name:
            if self._addform_validate:
                if Activity.objects.filter(offering__slug=self._course_slug, short_name=short_name).count() > 0:
                    raise forms.ValidationError('Activity with the same short name already exists')
            if self._editform_validate:
                if Activity.objects.filter(offering__slug=self._course_slug, short_name=short_name).exclude(slug=self._activity_slug).count() > 0:
                    raise forms.ValidationError('Activity with the same short name already exists')
        
        return short_name

    def _cant_change_group_reason(self, old_act):
        """
        Returns reason the group status can't be changed (or None if it can be).
        """
        if old_act.due_date and old_act.due_date < datetime.datetime.now():
            return 'due date has passed'
        if Submission.objects.filter(activity=old_act):
            return 'submissions have already been made'
        if NumericGrade.objects.filter(activity=old_act).exclude(flag="NOGR") \
                or LetterGrade.objects.filter(activity=old_act).exclude(flag="NOGR"):
            return 'grades have already been given'
        
        return None

    def clean_group(self):
        if self._addform_validate:
            # adding new activity: any value okay
            return self.cleaned_data['group']

        # get old version of activity and see if we're changing .group value
        old = Activity.objects.get(offering__slug=self._course_slug, slug=self._activity_slug)
        if self.cleaned_data['group'] is None:
            new_group = False
        else:
            new_group = GROUP_STATUS_MAP[self.cleaned_data['group']]
        
        if new_group != old.group:
            # attempting to switch group <-> individual: make sure that's allowed
            reason = self._cant_change_group_reason(old)
            if reason:
                raise forms.ValidationError('Cannot change group/individual status: ' + reason + '.')

        if new_group:
            # apparently 0 == True in this world.  Should fix GROUP_STATUS*
            return '0'
        else:
            return '1'

    def clean_extend_group(self):
        extend_group = self.cleaned_data['extend_group']
        if extend_group in ['None', '']:
            return None

        if 'group' not in self.cleaned_data or self.cleaned_data['group'] == '1':
            raise forms.ValidationError('Cannot extend groups on non-group activity.')
        
        if self._addform_validate:
            # adding new activity: any value okay
            return extend_group
        
        members = GroupMember.objects.filter(student__offering__slug=self._course_slug, activity__slug=self._activity_slug)
        if members:
            raise forms.ValidationError('Cannot extend groups: groups exist for this activity.')
        
        # have things started?
        old = Activity.objects.get(offering__slug=self._course_slug, slug=self._activity_slug)
        reason = self._cant_change_group_reason(old)
        if reason:
            raise forms.ValidationError('Cannot extend groups: ' + reason + '.')
        return extend_group


class NumericActivityForm(ActivityForm):
        
    status = forms.ChoiceField(choices=ACTIVITY_STATUS_CHOICES, initial='URLS',
            help_text='visibility of grades/activity to students')
    due_date = forms.SplitDateTimeField(required=False,
            help_text='Time format: HH:MM:SS, 24-hour time')
    max_grade = forms.DecimalField(max_digits=8, decimal_places=2, label='Maximum grade',
            help_text='Maximum grade for the activity',
            widget=forms.NumberInput(attrs={'class': 'gradeinput'}))
    group = forms.ChoiceField(label='Group activity', initial='1',
            choices=GROUP_STATUS_CHOICES,
            widget=forms.RadioSelect())
    extend_group = forms.ChoiceField(choices = [('NO', 'None')],
            label='Extend groups from', required=False,
            help_text='Extend groups from earlier group activity?')
    showstats = forms.BooleanField(initial=True, required=False,
            label="Show summary stats",
            help_text="Should students be able to view the summary stats: max, min, median, etc?")
    showhisto = forms.BooleanField(initial=True, required=False,
            label="Show histogram",
            help_text="Should students be able to view the grade distribution histogram?")

    def __init__(self, *args, **kwargs):
        try:
            tmp_act_list = kwargs.pop('previous_activities')
        except:
            tmp_act_list = [(None, 'Not available'),]

        super(NumericActivityForm, self).__init__(*args, **kwargs)

        self.fields['extend_group'].choices = tmp_act_list
    
class LetterActivityForm(ActivityForm):
    status = forms.ChoiceField(choices=ACTIVITY_STATUS_CHOICES, initial='URLS',
                               help_text='Visibility of grades/activity to students')
    due_date = forms.SplitDateTimeField(required=False,
                                        help_text='Time format: HH:MM:SS')
    group = forms.ChoiceField(label='Group activity', initial='1',
                              choices=GROUP_STATUS_CHOICES,
                              widget=forms.RadioSelect())
    extend_group = forms.ChoiceField(choices = [('NO', 'None')], required=False,
                                     label='Extend groups from',
                                     help_text = 'Extend groups from earlier group activities?')
    showstats = forms.BooleanField(initial=True, required=False,
            label="Show summary stats",
            help_text="Should students be able to view the summary stats: max, min, median, etc?")
    showhisto = forms.BooleanField(initial=True, required=False,
            label="Show histogram",
            help_text="Should students be able to view the grade distribution histogram?")

    def __init__(self, *args, **kwargs):
        try:
            tmp_act_list = kwargs.pop('previous_activities')
        except:
            tmp_act_list = [(None, 'Not available'),]

        super(LetterActivityForm, self).__init__(*args, **kwargs)

        self.fields['extend_group'].choices = tmp_act_list

class CalNumericActivityForm(ActivityForm):
    # default status is invisible
    status = forms.ChoiceField(choices=ACTIVITY_STATUS_CHOICES, initial='INVI',
                               help_text='Visibility of grades/activity to students')
    max_grade = forms.DecimalField(max_digits=8, decimal_places=2, label='Maximum grade',
                                   help_text='Maximum grade of the calculated result',
                                   widget=forms.NumberInput(attrs={'class': 'gradeinput'}))
    formula = forms.CharField(max_length=2000,
                    help_text=mark_safe('Formula to calculate the numeric grade: see <a href="#help">formula help</a> below for more info'),
                    widget=forms.Textarea(attrs={'rows':'6', 'cols':'40'}))
    showstats = forms.BooleanField(initial=True, required=False,
            label="Show summary stats",
            help_text="Should students be able to view the summary stats: max, min, median, etc?")
    showhisto = forms.BooleanField(initial=True, required=False,
            label="Show histogram",
            help_text="Should students be able to view the grade distribution histogram?")
    calculation_leak = forms.BooleanField(initial=False, required=False,
            label="Allow leaking unreleased",
            help_text="Include unreleased grades in the calculation, even after this grade is released? May leak unreleased grades to students.")

    def activate_addform_validation(self, course_slug):
        super(CalNumericActivityForm, self).activate_addform_validation(course_slug)
        self._course_numeric_activities = NumericActivity.objects.filter(offering__slug=course_slug, deleted=False)
        self.activity = None
        self.course = CourseOffering.objects.get(slug=course_slug)
        
    def activate_editform_validation(self, course_slug, activity_slug):
        super(CalNumericActivityForm, self).activate_editform_validation(course_slug, activity_slug)
        self._course_numeric_activities = NumericActivity.objects.exclude(slug=activity_slug).filter(offering__slug=course_slug, deleted=False)
        self.activity = CalNumericActivity.objects.get(offering__slug=course_slug, slug=activity_slug)
        self.course = self.activity.offering
    
    
    def clean_formula(self):
        formula = self.cleaned_data['formula']
        if formula:
            if self._addform_validate or self._editform_validate:
                try:
                    parse_and_validate_formula(formula, self.course, self.activity, self._course_numeric_activities)
                except ValidationError as e:
                    raise forms.ValidationError(e.args[0])
        return formula

class CalLetterActivityForm(ActivityForm):
    # default status is invisible
    status = forms.ChoiceField(choices=ACTIVITY_STATUS_CHOICES, initial='INVI',
                               help_text='visibility of grades/activity to students')
    
    numeric_activity = forms.ChoiceField(choices=[], label='Source Activity',
                                         help_text="Numeric grades that these letters will be based on")
    exam_activity = forms.ChoiceField(choices=[], required=False,
                                      help_text="The course's exam: used to guess N and DE grades where appropriate. Leave blank if you don't want these values guessed.")
    showstats = forms.BooleanField(initial=True, required=False,
            label="Show summary stats",
            help_text="Should students be able to view the summary stats: max, min, median, etc?")
    showhisto = forms.BooleanField(initial=True, required=False,
            label="Show histogram",
            help_text="Should students be able to view the grade distribution histogram?")
    
    def activate_addform_validation(self, course_slug):
        super(CalLetterActivityForm, self).activate_addform_validation(course_slug)
        self._course_letter_activities = LetterActivity.objects.filter(offering__slug=course_slug, deleted=False)
        
    def activate_editform_validation(self, course_slug, activity_slug):
        super(CalLetterActivityForm, self).activate_editform_validation(course_slug, activity_slug)
        self._course_letter_activities = LetterActivity.objects.exclude(slug=activity_slug).filter(offering__slug=course_slug, deleted=False)
    


##############################################################################################    
class ActivityFormEntry(forms.Form):
    status = forms.ChoiceField(choices=ACTIVITY_STATUS_CHOICES)
    value = forms.DecimalField(max_digits=8, decimal_places=2, required=False,
                               widget=forms.TextInput(attrs={'size':'4'}))
    
class Activity_ChoiceForm(forms.Form):
    choice = forms.ChoiceField(choices=ACTIVITY_TYPES)


class FormulaFormEntry(forms.Form):
    formula = forms.CharField(max_length=250,
                    help_text='Formula to calculate numeric grade',
                    widget=forms.Textarea(attrs={'rows':'6', 'cols':'40'}))
    
    def __init__(self, *args, **kwargs):
        super(FormulaFormEntry, self).__init__(*args, **kwargs)
        self._form_entry_validate = False
    
    def activate_form_entry_validation(self, course_slug, activity):
        self._form_entry_validate = True
        self._course_numeric_activities = NumericActivity.objects.filter(offering__slug=course_slug)
        self.activity = activity
        self.course = CourseOffering.objects.get(slug=course_slug)
    
    def clean_formula(self):
        formula = self.cleaned_data['formula']
        if formula:
            if self._form_entry_validate:
                try:
                    parsed_expr = parse_and_validate_formula(formula, self.course, self.activity, self._course_numeric_activities)
                except ValidationError as e:
                    raise forms.ValidationError(e.args[0])
                else:
                    self.pickled_formula = pickle.dumps(parsed_expr)
        return formula

class StudentSearchForm(forms.Form):
    search = forms.CharField(label="Userid or student number",
             widget=forms.TextInput(attrs={'size':'15'}))

class CourseConfigForm(forms.Form):
    from forum.models import IDENTITY_CHOICES
    url = forms.URLField(required=False, label='Course URL',
            help_text='Course home page address',
            widget=forms.TextInput(attrs={'size':'60'}))
    taemail = forms.EmailField(required=False, label="TA Contact Email",
            help_text="Email address to contact the TAs: set if you have a central contact address/list and don't want to encourage use of TAs' individual emails",)
    #discussion = forms.BooleanField(required=False, label='Discussion',
    #        help_text="Should the student/TA/instructor discussion forum be activated for this course?")
    forum = forms.BooleanField(required=False, label='Discussion Forum',
            help_text="Should the discussion forum be activated for this course?")
    forum_identity = forms.ChoiceField(required=True, label='Discussion Forum Anonymity', choices=IDENTITY_CHOICES,
            help_text='If using the discussion forum, what level of anonymity should be allowed for student posts? Identity is always known to the system in case of abuse.')
    #indiv_svn = forms.BooleanField(required=False, label="Individual SVN access",
    #        help_text="Can the instructor and TAs read students' individual Subversion repositories? Set only if they are being used explicitly for grading.")
    #instr_rw_svn = forms.BooleanField(required=False, label="Write SVN access",
    #        help_text="Can the instructor and TAs write to students' individual Subversion repositories?")
    group_min = forms.IntegerField(required=False, label="Minimum Group Size", initial=1, min_value=1, max_value=50,
            help_text="Smallest possible group. Entering 1 here implies students can work alone on group activities.",
            widget=forms.NumberInput(attrs={'class': 'smallnumberinput'}))
    group_max = forms.IntegerField(required=False, label="Maximum Group Size", initial=10, min_value=2, max_value=50,
            help_text="Largest possible group. Instructors can form larger groups, but students cannot.",
            widget=forms.NumberInput(attrs={'class': 'smallnumberinput'}))

    def clean(self):
        if 'group_min' in self.cleaned_data and 'group_max' in self.cleaned_data:
            gmin =  self.cleaned_data['group_min']
            gmax =  self.cleaned_data['group_max']
            if gmin and gmax and gmin > gmax:
                raise forms.ValidationError("Minimum group size can't be larger than maximum size.")
        return self.cleaned_data


class CutoffForm(forms.Form):
    ap = forms.DecimalField(max_digits=8, decimal_places=2, required=True)
    a = forms.DecimalField(max_digits=8, decimal_places=2, required=True)
    am = forms.DecimalField(max_digits=8, decimal_places=2, required=True)
    bp =forms.DecimalField(max_digits=8, decimal_places=2, required=True)
    b = forms.DecimalField(max_digits=8, decimal_places=2, required=True)
    bm = forms.DecimalField(max_digits=8, decimal_places=2, required=True)
    cp = forms.DecimalField(max_digits=8, decimal_places=2, required=True)
    c = forms.DecimalField(max_digits=8, decimal_places=2, required=True)
    cm = forms.DecimalField(max_digits=8, decimal_places=2, required=True)
    d = forms.DecimalField(max_digits=8, decimal_places=2, required=True)

    
    def clean(self):
        try:
            cutoffs = [self.cleaned_data['ap'], self.cleaned_data['a'],self.cleaned_data['am'],
                       self.cleaned_data['bp'], self.cleaned_data['b'],self.cleaned_data['bm'],
                       self.cleaned_data['cp'], self.cleaned_data['c'],self.cleaned_data['cm'],
                       self.cleaned_data['d']]
        except KeyError:
            raise forms.ValidationError('Some cutoff values entered incorrectly.')
        
        cut_copy = cutoffs[:]
        cut_copy.sort()
        cut_copy.reverse()
        if cut_copy != cutoffs:
            raise forms.ValidationError('Grade cutoffs must be in decreasing numeric order.')

        self.cleaned_data['cutoffs'] = cutoffs
        return self.cleaned_data

    def clean_ap(self):
        ap=self.cleaned_data['ap']
        if ap<0:
           raise forms.ValidationError('Grade cutoff must be positive.')
        return ap

    def clean_a(self):
        a=self.cleaned_data['a']
        if a<0:
           raise forms.ValidationError('Grade cutoff must be positive.')
        return a

    def clean_am(self):
        am=self.cleaned_data['am']
        if am<0:
           raise forms.ValidationError('Grade cutoff must be positive.')
        return am

    def clean_bp(self):
        bp=self.cleaned_data['bp']
        if bp<0:
           raise forms.ValidationError('Grade cutoff must be positive.')
        return bp

    def clean_b(self):
        b=self.cleaned_data['b']
        if b<0:
           raise forms.ValidationError('Grade cutoff must be positive.')
        return b

    def clean_bm(self):
        bm=self.cleaned_data['bm']
        if bm<0:
           raise forms.ValidationError('Grade cutoff must be positive.')
        return bm

    def clean_cp(self):
        cp=self.cleaned_data['cp']
        if cp<0:
           raise forms.ValidationError('Grade cutoff must be positive.')
        return cp

    def clean_c(self):
        c=self.cleaned_data['c']
        if c<0:
           raise forms.ValidationError('Grade cutoff must be positive.')
        return c

    def clean_cm(self):
        cm=self.cleaned_data['cm']
        if cm<0:
           raise forms.ValidationError('Grade cutoff must be positive.')
        return cm

    def clean_d(self):
        d=self.cleaned_data['d']
        if d<0:
           raise forms.ValidationError('Grade cutoff must be positive.')
        return d


class MessageForm(MarkupContentMixin(), forms.ModelForm):
    content = MarkupContentField(rows=10, with_wysiwyg=False, default_markup='textile', allow_math=False,
                                 restricted=True)

    class Meta:
        model = NewsItem
        # these fields are decided from the request at the time the form is submitted
        exclude = ['user', 'author', 'published','updated','source_app','course', 'read', 'config']



