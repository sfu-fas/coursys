# imitating from test_without_migrations internals, so we always get that behaviour
# from https://github.com/henriquebastos/django-test-without-migrations/blob/master/test_without_migrations/management/commands/test.py

class DisableMigrations(object):
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return "notmigrations"