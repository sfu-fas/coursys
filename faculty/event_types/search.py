import copy
import operator

from django import forms
from django.utils.safestring import mark_safe
from django.forms.utils import pretty_name


class SearchRule(object):

    OPERATOR_CHOICES = ()

    def __init__(self, name, field, Handler):
        self.field_name = name
        self.field = field
        self.Handler = Handler

        if hasattr(Handler, 'SEARCH_FIELD_NAMES') and name in Handler.SEARCH_FIELD_NAMES:
            prettyname = Handler.SEARCH_FIELD_NAMES[name]
        else:
            prettyname = pretty_name(self.field_name)
        self.pretty_field_name = prettyname

    def make_operator_field(self, viewer, member_units):
        return forms.ChoiceField(choices=self.OPERATOR_CHOICES, label='', required=False)

    def make_value_field(self, viewer, member_units):
        field = copy.deepcopy(self.field)
        field.label = ''
        field.required = False
        field.initial = ''
        return field

    def make_fields(self, viewer, member_units):
        return (
            ('operator', self.make_operator_field(viewer, member_units)),
            ('value', self.make_value_field(viewer, member_units)),
        )

    def make_form(self, viewer, member_units, data=None):
        Form = type('SearchRuleForm', (forms.Form,), dict(self.make_fields(viewer, member_units)))

        if data:
            form = Form(data, prefix=self.field_name)
        else:
            form = Form(prefix=self.field_name)

        # XXX: Hack to make 'operator' show up before 'value'
        value = form.fields.pop('value')
        form.fields['value'] = value
        return form

    def matches(self, handler, form):
        return True


class ComparableSearchRule(SearchRule):

    OPERATOR_CHOICES = (
        ('', '----'),
        ('eq', 'EQUAL TO'),
        ('lt', 'LESS THAN'),
        ('gt', 'GREATER THAN'),
    )
    OPERATORS = {
        'eq': operator.eq,
        'lt': operator.lt,
        'gt': operator.gt,
    }

    def matches(self, handler, form):
        op_func = self.OPERATORS.get(form.cleaned_data['operator'])
        if op_func:
            return op_func(handler.get_config(self.field_name),
                           form.cleaned_data['value'])
        else:
            return True


class ChoiceSearchRule(SearchRule):

    def make_value_field(self, viewer, member_units):
        field = super(ChoiceSearchRule, self).make_value_field(viewer, member_units)

        if self.field.required and not isinstance(self.field, forms.ModelChoiceField):
            field.choices = (('', mark_safe('&mdash;')),) + tuple(field.choices)
        field.initial = ''

        return field

    def make_fields(self, viewer, member_units):
        return (
            ('value', self.make_value_field(viewer, member_units)),
        )

    def matches(self, handler, form):
        if form.cleaned_data['value']:
            return handler.get_config(self.field_name) == form.cleaned_data['value']
        else:
            return True


class StringSearchRule(SearchRule):

    OPERATOR_CHOICES = (
        ('contains', 'CONTAINS'),
        ('equals', 'EQUALS'),
    )

    def make_value_field(self, viewer, member_units):
        return forms.CharField(label='', required=False)

    def matches(self, handler, form):
        op = form.cleaned_data['operator']
        value = form.cleaned_data['value']

        if op and value:
            real_value = handler.get_display(self.field_name)

            if op == 'contains':
                return value.lower() in real_value.lower()
            elif op == 'equals':
                return value == real_value
        else:
            return True


class BooleanSearchRule(SearchRule):

    CHOICES = (
        ('', '----'),
        ('yes', 'YES'),
        ('no', 'NO'),
    )

    def make_value_field(self, viewer, member_units):
        return forms.ChoiceField(choices=self.CHOICES, initial='', label='', required=False)

    def make_fields(self, viewer, member_units):
        return (
            ('value', self.make_value_field(viewer, member_units)),
        )

    def matches(self, handler, form):
        op = form.cleaned_data['value']

        if op == 'yes':
            return bool(handler.get_config(self.field_name))
        elif op == 'no':
            return not handler.get_config(self.field_name)
        else:
            return True
