from django import forms
from django.conf import settings
from grades.models import ACTIVITY_STATUS_CHOICES, NumericActivity, LetterActivity, CalNumericActivity, Activity, NumericGrade, LetterGrade,ACTIVITY_TYPES, LETTER_GRADE_CHOICES
from coredata.models import CourseOffering
from groups.models import GroupMember
from django.utils.safestring import mark_safe
import pickle
from grades.formulas import parse, activities_dictionary, cols_used
from pyparsing import ParseException
from django.forms.util import ErrorList
import datetime, decimal
from grades.utils import parse_and_validate_formula, ValidationError
from submission.models import Submission
from dashboard.models import NewsItem

_required_star = '<span><img src="'+settings.STATIC_URL+'icons/required_star.gif" alt="required"/></span>'

FORMTYPE = {'add': 'add', 'edit': 'edit'}
GROUP_STATUS_CHOICES = [
    ('0', 'Yes'),
    ('1', 'No') ]
GROUP_STATUS = dict(GROUP_STATUS_CHOICES)
GROUP_STATUS_MAP = {'0': True, '1': False}

class CustomSplitDateTimeWidget(forms.SplitDateTimeWidget):
    """
    Create a custom SplitDateTimeWidget with custom html output format
    """
    def __init__(self, attrs=None, date_format=None, time_format=None):
        super(CustomSplitDateTimeWidget, self).__init__(attrs, date_format, time_format)

    def value_from_datadict(self, data, files, name):
        """
        Quick dirty solution.
        Fix SplitDateTimeWidget bugs when displaying the form with SplitDateTimeField.
        (Original problem: SplitDateTimeField can not display the field data into the seperated
        DateInput and TimeInput)
        """
        if data.has_key(name):
            # need to manually split the datetime into date and time for later data retrieval
            if isinstance(data[name], datetime.datetime):
                if isinstance(self.widgets[0], forms.DateInput) and isinstance(self.widgets[1], forms.TimeInput):
                    data[name + '_0'] = data[name].date()
                    data[name + '_1'] = data[name].time()
        return [widget.value_from_datadict(data, files, name + '_%s' % i) for i, widget in enumerate(self.widgets)]
        
    def format_output(self, rendered_widgets):
        return mark_safe(u'<div class="datetime">%s %s<br />%s %s</div>' % \
            (('Date:'), rendered_widgets[0], ('Time:'), rendered_widgets[1]))

class ActivityForm(forms.Form):
    name = forms.CharField(max_length=30, label=mark_safe('Name:'+_required_star),
                    help_text='name of the activity, e.g "Assignment 1" or "Midterm"',
                    widget=forms.TextInput(attrs={'size':'30'}))
    short_name = forms.CharField(max_length=15, label=mark_safe('Short name:' + _required_star),
                                help_text='short version of the name for column headings, e.g. "A1" or "MT"',
                                widget=forms.TextInput(attrs={'size':'8'}))
    percent = forms.DecimalField(max_digits=5, decimal_places=2, required=False, label='Percentage:',
                                 help_text='percent of final mark',
                                 widget=forms.TextInput(attrs={'size':'2'}))
    url = forms.URLField(required=False, label='URL:',
                                 help_text='page for more information, e.g. assignment description or exam info',
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
                    raise forms.ValidationError(u'Activity with the same name already exists')
            if self._editform_validate:
                if Activity.objects.filter(offering__slug=self._course_slug, name=name).exclude(slug=self._activity_slug).count() > 0:
                    raise forms.ValidationError(u'Activity with the same name already exists')
        
        return name
    
    def clean_short_name(self):
        short_name = self.cleaned_data['short_name']
        if short_name:
            if self._addform_validate:
                if Activity.objects.filter(offering__slug=self._course_slug, short_name=short_name).count() > 0:
                    raise forms.ValidationError(u'Activity with the same short name already exists')
            if self._editform_validate:
                if Activity.objects.filter(offering__slug=self._course_slug, short_name=short_name).exclude(slug=self._activity_slug).count() > 0:
                    raise forms.ValidationError(u'Activity with the same short name already exists')
        
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
        if extend_group == 'None':
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
            label=mark_safe('Status:' + _required_star),
            help_text='visibility of grades/activity to students')
    due_date = forms.SplitDateTimeField(label=mark_safe('Due date:'), required=False,
            help_text='Time format: HH:MM:SS, 24-hour time',
            widget=CustomSplitDateTimeWidget())
    max_grade = forms.DecimalField(max_digits=8, decimal_places=2, label=mark_safe('Maximum grade:' + _required_star),
            help_text='maximum grade for the activity',
            widget=forms.TextInput(attrs={'size':'3'}))
    group = forms.ChoiceField(label=mark_safe('Group activity:' + _required_star), initial='1',
            choices=GROUP_STATUS_CHOICES,
            widget=forms.RadioSelect())
    extend_group = forms.ChoiceField(choices = [('NO', 'None')],
            label=mark_safe('Extend groups from:'),
            help_text = 'extend groups from earlier group activities')
    showstats = forms.BooleanField(initial=True, required=False,
            label="Show summary stats:", 
            help_text="Should students be able to view the summary stats: max, min, median, etc?")
    showhisto = forms.BooleanField(initial=True, required=False,
            label="Show histogram:", 
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
                               label=mark_safe('Status:' + _required_star),
                               help_text='visibility of grades/activity to students')
    due_date = forms.SplitDateTimeField(label=mark_safe('Due date:'), required=False,
                                        help_text='Time format: HH:MM:SS',
                                        widget=CustomSplitDateTimeWidget())
    group = forms.ChoiceField(label=mark_safe('Group activity:' + _required_star), initial='1',
                              choices=GROUP_STATUS_CHOICES,
                              widget=forms.RadioSelect())
    extend_group = forms.ChoiceField(choices = [('NO', 'None')],
                                     label=mark_safe('Extend groups from:'),
                                     help_text = 'extend groups from earlier group activities')
    showstats = forms.BooleanField(initial=True, required=False,
            label="Show summary stats:", 
            help_text="Should students be able to view the summary stats: max, min, median, etc?")
    showhisto = forms.BooleanField(initial=True, required=False,
            label="Show histogram:", 
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
                               label=mark_safe('Status:' + _required_star),
                               help_text='visibility of grades/activity to students')
    max_grade = forms.DecimalField(max_digits=8, decimal_places=2, label=mark_safe('Maximum grade:' + _required_star),
                                   help_text='maximum grade of the calculated result',
                                   widget=forms.TextInput(attrs={'size':'3'}))
    formula = forms.CharField(max_length=2000, label=mark_safe('Formula:'+_required_star),
                    help_text=mark_safe('formula to calculate the numeric grade: see <a href="#help">formula help</a> below for more info'),
                    widget=forms.Textarea(attrs={'rows':'6', 'cols':'40'}))
    showstats = forms.BooleanField(initial=True, required=False,
            label="Show summary stats:", 
            help_text="Should students be able to view the summary stats: max, min, median, etc?")
    showhisto = forms.BooleanField(initial=True, required=False,
            label="Show histogram:", 
            help_text="Should students be able to view the grade distribution histogram?")
    
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
                               label=mark_safe('Status:' + _required_star),
                               help_text='visibility of grades/activity to students')
    
    numeric_activity = forms.ChoiceField(choices=[], label=mark_safe('Source Activity:' + _required_star),
                                         help_text="numeric grades that these letters will be based on")
    exam_activity = forms.ChoiceField(choices=[], required=False,
                                      help_text="the course's exam: used to guess N and DE grades where appropriate.  Leave blank if you don't want these values guessed.")
    showstats = forms.BooleanField(initial=True, required=False,
            label="Show summary stats:", 
            help_text="Should students be able to view the summary stats: max, min, median, etc?")
    showhisto = forms.BooleanField(initial=True, required=False,
            label="Show histogram:", 
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
    formula = forms.CharField(max_length=250, label=mark_safe('Formula:'+_required_star),
                    help_text='parsed formula to calculate final numeric grade',
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
    url = forms.URLField(required=False, label='Course URL',
            help_text='Course home page address',
            widget=forms.TextInput(attrs={'size':'60'}))
    taemail = forms.EmailField(required=False, label="TA Contact Email",
            help_text="Email address to contact the TAs: set if you have a central contact address/list and don't want to encourage use of TAs' individual emails",)
    discussion = forms.BooleanField(required=False, label='Discussion',
            help_text="Should the student/TA/instructor discussion forum be activated for this course?")
    indiv_svn = forms.BooleanField(required=False, label="Individual SVN access",
            help_text="Can the instructor and TAs access students' indivdual Subversion repositories? Set only if they are being used explicitly for grading.")


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
        if c>100 or c<0:
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


class MessageForm(forms.ModelForm):
    class Meta:
        model = NewsItem
        # these fields are decided from the request at the time the form is submitted
        exclude = ['user', 'author', 'published','updated','source_app','course', 'read']



