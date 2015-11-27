from django.apps import AppConfig
from django.core.checks import register

from .checks import bitfield_check

class CoredataConfig(AppConfig):
    name = 'coredata'

    def ready(self):
        # override to register the system check
        register(bitfield_check)