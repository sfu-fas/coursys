import copy
import operator

from django import forms
from django.forms.forms import pretty_name


class SearchRule(object):

    OPERATOR_CHOICES = ()

    def __init__(self, name, field, Handler):
        self.field_name = name
        self.field = field
        self.Handler = Handler
        self.pretty_field_name = pretty_name(self.field_name)

    def make_operator_field(self):
        return forms.ChoiceField(choices=self.OPERATOR_CHOICES, label='', required=False)

    def make_value_field(self):
        field = copy.deepcopy(self.field)
        field.label = ''
        field.required = False
        field.initial = ''
        return field

    def make_fields(self):
        return (
            ('operator', self.make_operator_field()),
            ('value', self.make_value_field()),
        )

    def make_form(self, data=None):
        Form = type('SearchRuleForm', (forms.Form,), dict(self.make_fields()))

        if data:
            form = Form(data, prefix=self.field_name)
        else:
            form = Form(prefix=self.field_name)

        # XXX: Hack to make 'operator' show up before 'value'
        form.fields.keyOrder.sort()
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

    def make_value_field(self):
        field = super(ChoiceSearchRule, self).make_value_field()

        if self.field.required and not isinstance(self.field, forms.ModelChoiceField):
            field.choices = (('', '----'),) + tuple(field.choices)
        field.initial = ''

        return field

    def make_fields(self):
        return (
            ('value', self.make_value_field()),
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

    def make_value_field(self):
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

    def make_value_field(self):
        return forms.ChoiceField(choices=self.CHOICES, initial='', label='', required=False)

    def make_fields(self):
        return (
            ('value', self.make_value_field()),
        )

    def matches(self, handler, form):
        op = form.cleaned_data['value']

        if op == 'yes':
            return bool(handler.get_config(self.field_name))
        elif op == 'no':
            return not handler.get_config(self.field_name)
        else:
            return True
