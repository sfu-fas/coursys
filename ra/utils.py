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

def get_ra_definition(unit=None):
    return SystemVariable.get_value('ra_definition', unit)

def get_gras_definition(unit=None):
    return SystemVariable.get_value('gras_definition', unit) 

def get_nc_definition(unit=None):
    return SystemVariable.get_value('nc_definition', unit)

def get_usra_definition(unit=None):
    return SystemVariable.get_value('usra_definition', unit)

def get_gras_funding_intro(unit=None):
    return SystemVariable.get_value('gras_funding_intro', unit)

def get_nc_funding_intro(unit=None):
    return SystemVariable.get_value('nc_funding_intro', unit)

def get_ra_funding_intro(unit=None):
    return SystemVariable.get_value('ra_funding_intro', unit)

def get_ishf_info(unit=None):
    return SystemVariable.get_value('ishf_info', unit)

def get_vacation_pay_help_text(unit=None):
    return SystemVariable.get_value('vacation_pay_help_text', unit)

def get_biweekly_hours_error_text(unit=None):
    return SystemVariable.get_value('biweekly_hours_error_text', unit)