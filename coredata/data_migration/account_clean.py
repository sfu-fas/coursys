import sys, os
sys.path.append(".")
sys.path.append("..")
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from django.db import transaction
from ra.models import Account
from coredata.models import Unit

correct_accounts = [
    (5261,'Research Scientists'),
    (5263,'Research Associates'),
    (5262,'Visiting Scientists'),
    (5264,'M.Sc. RA - Canadian'),
    (5278,'Ph.D. RA - Foreign'),
    (5272,'Undergrad RA - Canadian'),
    (5277,'Ph.D. RA - Canadian'),
    (5266,'Hourly Staff - Non Student'),
    (5265,'M.Sc. RA - Foreign'),
    (5282,'Hourly Staff - Students'),
    (5273,'Research PostDoc - Canadian'),
    (5274,'RA - Non Student'),
    (5275,'Undergrad RA - Foreign'),
    (5276,'Research PostDoc - Foreign'),
    ]

cmpt = Unit.objects.get(slug='cmpt')

@transaction.commit_on_success
def hide_old():
    old_acct = Account.objects.filter(unit=cmpt, account_number=0)
    old_acct.update(hidden=True)

@transaction.commit_on_success
def add_correct():
    for account_number, title in correct_accounts:
        try:
            Account.objects.get(unit=cmpt, account_number=account_number)
        except Account.DoesNotExist:
            a=Account(unit=cmpt, account_number=account_number, position_number=1, title=title)
            a.save()

hide_old()
add_correct()
