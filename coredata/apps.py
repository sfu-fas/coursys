from django.apps import AppConfig

class CoredataConfig(AppConfig):
    name = 'coredata'


from django.core.checks import Warning, register
from django.conf import settings
@register()
def sqlite_check(app_configs, **kwargs):
    errors = []
    if 'sqlite' not in settings.DATABASES['default']['ENGINE']:
        # not using sqlite, so don't worry
        return errors

    import sqlite3
    if sqlite3.sqlite_version_info < (3, 12):
        errors.append(
            Warning(
                'SQLite version problem',
                hint='A bug is sqlite version 3.11.x causes a segfault in our tests. Upgrading to >=3.14 is suggested. This is only a warning because many things still work. Just not the tests.',
                id='coredata.E001',
            )
        )
    return errors