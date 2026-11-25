import datetime

from system.models import SystemVariable

def get_contact_email(unit=None):
    value = SystemVariable.get_value('ra_contact_email', unit)
    return value if value is not None else ''

def get_ra_intro_html(unit=None):
    value = SystemVariable.get_value('ra_intro_html', unit)
    return value if value is not None else ''

def get_min_wage(unit=None):
    value = SystemVariable.get_value('min_wage', unit)
    return value if value is not None else 0.0

def get_new_min_wage(unit=None):
    value = SystemVariable.get_value('new_min_wage', unit)
    return value if value is not None else 0.0

def get_new_min_wage_date(unit=None):
    value = SystemVariable.get_value('new_min_wage_date', unit)
    return value if value is not None else datetime.date(2000, 1, 1)

def get_ishf_fee(unit=None):
    value = SystemVariable.get_value('ishf_fee', unit)
    return value if value is not None else 0.0

def get_new_ra_wage_date(unit=None):
    value = SystemVariable.get_value('new_ra_wage_date', unit)
    return value if value is not None else datetime.date(2000, 1, 1)

def get_new_ra_wage(unit=None):
    value = SystemVariable.get_value('new_ra_wage', unit)
    return value if value is not None else 0.0

def get_ra_definition(unit=None):
    value = SystemVariable.get_value('ra_definition', unit)
    return value if value is not None else ''

def get_gras_definition(unit=None):
    value = SystemVariable.get_value('gras_definition', unit)
    return value if value is not None else ''

def get_nc_definition(unit=None):
    value = SystemVariable.get_value('nc_definition', unit)
    return value if value is not None else ''

def get_usra_definition(unit=None):
    value = SystemVariable.get_value('usra_definition', unit)
    return value if value is not None else ''

def get_gras_funding_intro(unit=None):
    value = SystemVariable.get_value('gras_funding_intro', unit)
    return value if value is not None else ''

def get_nc_funding_intro(unit=None):
    value = SystemVariable.get_value('nc_funding_intro', unit)
    return value if value is not None else ''

def get_ra_funding_intro(unit=None):
    value = SystemVariable.get_value('ra_funding_intro', unit)
    return value if value is not None else ''

def get_ishf_info(unit=None):
    value = SystemVariable.get_value('ishf_info', unit)
    return value if value is not None else ''

def get_vacation_pay_help_text(unit=None):
    value = SystemVariable.get_value('vacation_pay_help_text', unit)
    return value if value is not None else ''

def get_biweekly_hours_error_text(unit=None):
    value = SystemVariable.get_value('biweekly_hours_error_text', unit)
    return value if value is not None else ''