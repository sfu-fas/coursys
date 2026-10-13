from system.models import SystemVariable

def get_contact_email(unit=None):
    return SystemVariable.get_value('ra_contact_email', unit)

def get_ra_intro_html(unit=None):
    return SystemVariable.get_value('ra_intro_html', unit)

def get_min_wage(unit=None):
    return SystemVariable.get_value('min_wage', unit)

def get_new_min_wage(unit=None):
    return SystemVariable.get_value('new_min_wage', unit)

def get_new_min_wage_date(unit=None):
    return SystemVariable.get_value('new_min_wage_date', unit)

def get_ishf_fee(unit=None):
    return SystemVariable.get_value('ishf_fee', unit)

def get_new_ra_wage_date(unit=None):
    return SystemVariable.get_value('new_ra_wage_date', unit)

def get_new_ra_wage(unit=None):
    return SystemVariable.get_value('new_ra_wage', unit)