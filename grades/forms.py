from django import forms
from django.conf import settings
from grades.models import ACTIVITY_STATUS_CHOICES, NumericActivity, LetterActivity, Activity, NumericGrade, LetterGrade,ACTIVITY_TYPES, LETTER_GRADE_CHOICES
from django.utils.safestring import mark_safe
import pickle
from grades.formulas import parse, activities_dictionary, cols_used
from pyparsing import ParseException
from django.forms.util import ErrorList
import datetime
from grades.utils import parse_and_validate_formula, ValidationError
from submission.models import Submission

_required_star = '<span><img src="'+settings.MEDIA_URL+'icons/required_star.gif" alt="required"/></span>'

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
    url = forms.URLField(required=False, verify_exists=True, label='URL:',
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
                if Activity.objects.filter(offering__slug=self._course_slug, name=name, deleted=False).count() > 0:
                    raise forms.ValidationError(u'Activity with the same name already exists')
            if self._editform_validate:
                if Activity.objects.filter(offering__slug=self._course_slug, name=name, deleted=False).exclude(slug=self._activity_slug).count() > 0:
                    raise forms.ValidationError(u'Activity with the same name already exists')
        
        return name
    
    def clean_short_name(self):
        short_name = self.cleaned_data['short_name']
        if short_name:
            if self._addform_validate:
                if Activity.objects.filter(offering__slug=self._course_slug, short_name=short_name, deleted=False).count() > 0:
                    raise forms.ValidationError(u'Activity with the same short name already exists')
            if self._editform_validate:
                if Activity.objects.filter(offering__slug=self._course_slug, short_name=short_name, deleted=False).exclude(slug=self._activity_slug).count() > 0:
                    raise forms.ValidationError(u'Activity with the same short name already exists')
        
        return short_name

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
            if old.due_date and old.due_date < datetime.datetime.now():
                raise forms.ValidationError('Cannot change group/individual status: due date has passed.')
            if Submission.objects.filter(activity=old):
                raise forms.ValidationError('Cannot change group/individual status: submissions have already been made.')
            if NumericGrade.objects.filter(activity=old).exclude(flag="NOGR") \
                    or LetterGrade.objects.filter(activity=old).exclude(flag="NOGR"):
                raise forms.ValidationError('Cannot change group/individual status: grades have already been given.')

        if new_group:
            # apparently 0 == True in this world.  Should fix GROUP_STATUS*
            return '0'
        else:
            return '1'

class NumericActivityForm(ActivityForm):
        
    status = forms.ChoiceField(choices=ACTIVITY_STATUS_CHOICES, initial='URLS',
                               label=mark_safe('Status:' + _required_star),
                               help_text='visibility of grades/activity to students')
    due_date = forms.SplitDateTimeField(label=mark_safe('Due date:'), required=False,
                                        help_text='Time format: HH:MM:SS',
                                        widget=CustomSplitDateTimeWidget())
    max_grade = forms.DecimalField(max_digits=5, decimal_places=2, label=mark_safe('Maximum grade:' + _required_star),
                                   help_text='maximum grade for the activity',
                                   widget=forms.TextInput(attrs={'size':'3'}))
    group = forms.ChoiceField(label=mark_safe('Group activity:' + _required_star), initial='1',
                              choices=GROUP_STATUS_CHOICES,
                              widget=forms.RadioSelect())
    extend_group = forms.ChoiceField(choices = [('NO', 'None')],
                                     label=mark_safe('Extend groups from:'),
                                     help_text = 'extend groups from earlier group activities')

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
    max_grade = forms.DecimalField(max_digits=5, decimal_places=2, label=mark_safe('Maximum grade:' + _required_star),
                                   help_text='maximum grade of the calculated result',
                                   widget=forms.TextInput(attrs={'size':'3'}))
    formula = forms.CharField(max_length=250, label=mark_safe('Formula:'+_required_star),
                    help_text='parsed formula to calculate final numeric grade',
                    widget=forms.Textarea(attrs={'rows':'6', 'cols':'40'}))
    
    def activate_addform_validation(self, course_slug):
        super(CalNumericActivityForm, self).activate_addform_validation(course_slug)
        self._course_numeric_activities = NumericActivity.objects.filter(offering__slug=course_slug)
        
    def activate_editform_validation(self, course_slug, activity_slug):
        super(CalNumericActivityForm, self).activate_editform_validation(course_slug, activity_slug)
        self._course_numeric_activities = NumericActivity.objects.exclude(slug=activity_slug).filter(offering__slug=course_slug)
    
    def clean_formula(self):
        formula = self.cleaned_data['formula']
        if formula:
            if self._addform_validate or self._editform_validate:
                try:
                    parse_and_validate_formula(formula, self._course_numeric_activities)
                except ValidationError as e:
                    raise forms.ValidationError(e.args[0])
        return formula
#################################################YU LIU Added#############################
class CalLetterActivityForm(ActivityForm):
    # default status is invisible
    status = forms.ChoiceField(choices=ACTIVITY_STATUS_CHOICES, initial='INVI',
                               label=mark_safe('Status:' + _required_star),
                               help_text='visibility of grades/activity to students')
    
    numeric_activity = forms.ChoiceField(choices=[], label=mark_safe('Source Activity:' + _required_star),
                                         help_text="numeric grades that these letters will be based on")
    exam_activity = forms.ChoiceField(choices=[], required=False,
                                      help_text="the course's exam: used to guess N and DE grades where appropriate.  Leave blank if you don't want these values guessed.")
    
    def activate_addform_validation(self, course_slug):
        super(CalLetterActivityForm, self).activate_addform_validation(course_slug)
        self._course_letter_activities = LetterActivity.objects.filter(offering__slug=course_slug)
        
    def activate_editform_validation(self, course_slug, activity_slug):
        super(CalLetterActivityForm, self).activate_editform_validation(course_slug, activity_slug)
        self._course_letter_activities = LetterActivity.objects.exclude(slug=activity_slug).filter(offering__slug=course_slug)
    


##############################################################################################    
class ActivityFormEntry(forms.Form):
    status = forms.ChoiceField(choices=ACTIVITY_STATUS_CHOICES)
    value = forms.DecimalField(max_digits=5, decimal_places=2, required=False,
                               widget=forms.TextInput(attrs={'size':'3'}))
    
class Activity_ChoiceForm(forms.Form):
    choice = forms.ChoiceField(choices=ACTIVITY_TYPES)


class FormulaFormEntry(forms.Form):
    formula = forms.CharField(max_length=250, label=mark_safe('Formula:'+_required_star),
                    help_text='parsed formula to calculate final numeric grade',
                    widget=forms.Textarea(attrs={'rows':'6', 'cols':'40'}))
    
    def __init__(self, *args, **kwargs):
        super(FormulaFormEntry, self).__init__(*args, **kwargs)
        self._form_entry_validate = False
    
    def activate_form_entry_validation(self, course_slug):
        self._form_entry_validate = True
        self._course_numeric_activities = NumericActivity.objects.filter(offering__slug=course_slug)
    
    def clean_formula(self):
        formula = self.cleaned_data['formula']
        if formula:
            if self._form_entry_validate:
                try:
                    parsed_expr = parse_and_validate_formula(formula, self._course_numeric_activities)
                except ValidationError as e:
                    raise forms.ValidationError(e.args[0])
                else:
                    self.pickled_formula = pickle.dumps(parsed_expr)
        return formula

class StudentSearchForm(forms.Form):
    search = forms.CharField(label="Userid or student number",
             widget=forms.TextInput(attrs={'size':'15'}))

class URLForm(forms.Form):
    url = forms.URLField(required=False, verify_exists=True, label='URL:',
                                 help_text='Course home page address',
                                 widget=forms.TextInput(attrs={'size':'60'}))


class CutoffForm(forms.Form):
    ap = forms.DecimalField(max_digits=4, decimal_places=2,required=True)
    a = forms.DecimalField(max_digits=4, decimal_places=2)
    am = forms.DecimalField(max_digits=4, decimal_places=2)
    bp =forms.DecimalField(max_digits=4, decimal_places=2)
    b = forms.DecimalField(max_digits=4, decimal_places=2)
    bm = forms.DecimalField(max_digits=4, decimal_places=2)
    cp = forms.DecimalField(max_digits=4, decimal_places=2)
    c = forms.DecimalField(max_digits=4, decimal_places=2)
    cm = forms.DecimalField(max_digits=4, decimal_places=2)
    d = forms.DecimalField(max_digits=4, decimal_places=2)


    def clean_ap(self):
	ap=self.cleaned_data['ap']
        if ap>100 or ap<0:
           raise forms.ValidationError('Please input valid numberic grade')
        return ap


    def clean_ap(self):
	ap=self.cleaned_data['ap']
        if ap>100 or ap<0:
           raise forms.ValidationError('Please input valid numberic grade')
        return ap

    def clean_a(self):
	a=self.cleaned_data['a']
        if a>100 or a<0:
           raise forms.ValidationError('Please input valid numberic grade')
        return a

    def clean_am(self):
	am=self.cleaned_data['am']
        if am>100 or am<0:
           raise forms.ValidationError('Please input valid numberic grade')
        return am

    def clean_bp(self):
	bp=self.cleaned_data['bp']
        if bp>100 or bp<0:
           raise forms.ValidationError('Please input valid numberic grade')
        return bp

    def clean_b(self):
	b=self.cleaned_data['b']
        if b>100 or b<0:
           raise forms.ValidationError('Please input valid numberic grade')
        return b

    def clean_bm(self):
	bm=self.cleaned_data['bm']
        if bm>100 or bm<0:
           raise forms.ValidationError('Please input valid numberic grade')
        return bm

    def clean_cp(self):
	cp=self.cleaned_data['cp']
        if cp>100 or cp<0:
           raise forms.ValidationError('Please input valid numberic grade')
        return cp

    def clean_c(self):
	c=self.cleaned_data['c']
        if c>100 or c<0:
           raise forms.ValidationError('Please input valid numberic grade')
        return c

    def clean_cm(self):
	cm=self.cleaned_data['cm']
        if cm>100 or cm<0:
           raise forms.ValidationError('Please input valid numberic grade')
        return cm

    def clean_d(self):
	d=self.cleaned_data['d']
        if d>100 or d<0:
           raise forms.ValidationError('Please input valid numberic grade')
        return d



