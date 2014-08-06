# Django
from django import forms
from django.core.exceptions import ValidationError

class GuessPayperiodsWidget(forms.TextInput):
    """
    A widget to guess at pay-periods. 
    Assumes that you have fields named "pay_start", "pay_end", and "payperiods"
    """
    def render(self, name, value, attrs=None):
        if not attrs:
            attrs={'class':'autocomplete_person'}
        elif not 'class' in attrs:
            attrs['class'] = 'autocomplete_person'
        else:
            attrs['class'] = attrs['class'] + " autocomplete_person"
        html = super(GuessPayperiodsWidget, self).render(name, value, attrs)
        html += "<script type='application/javascript'>"
        html += "function guess_pay_periods(){"
        html += "  date_1 = $('#id_pay_start').val(); "
        html += "  date_2 = $('#id_pay_end').val(); "
        html += "  moment_1 = moment(date_1, 'YYYY-MM-DD'); "
        html += "  moment_2 = moment(date_2, 'YYYY-MM-DD'); "
        html += "  days = Math.abs(moment_2.diff(moment_1, 'days'))+1;"
        html += "  payperiods = Math.round(days/14);"
        html += "  $('#id_payperiods').val(payperiods);"
        html += "  $('#id_payperiods').effect('highlight');"
        html += "}"
        html += "$('#id_pay_start').change(guess_pay_periods);"
        html += "$('#id_pay_end').change(guess_pay_periods);"
        html += "</script>"
        return html

    class Media:
        js = ('moment.min.js',)

