from system.models import SystemVariable

def get_postdoc_intro_html(unit=None):
    return SystemVariable.get_value('postdoc_intro_html', unit)
