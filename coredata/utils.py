from system.models import SystemVariable

def get_banner_message_index(unit=None):
    return SystemVariable.get_value('banner_message_index', unit)

def get_banner_message(unit=None):
    return SystemVariable.get_value('banner_message', unit)