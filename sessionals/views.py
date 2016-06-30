from courselib.auth import requires_role
from .models import SessionalAccount, SessionalContract
from .forms import SessionalAccountForm, SessionalContractForm
from django.shortcuts import render, HttpResponseRedirect, get_object_or_404, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib import messages
from log.models import LogEntry
from datetime import datetime
from courselib.search import find_userid_or_emplid
from coredata.models import AnyPerson



@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def sessionals_index(request):
    print "got to index gi"
    return render(request, 'sessionals/index.html')


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def manage_accounts(request):
    accounts = SessionalAccount.objects.visible(request.units)
    return render(request, 'sessionals/manage_accounts.html')


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def new_account(request):
    if request.method == 'POST':
        form = SessionalAccountForm(request, request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Account was created.'
                                 )
            l = LogEntry(userid=request.user.username,
                         description="added account: %s" % (account),
                         related_object=account
                         )
            l.save()

            return HttpResponseRedirect(reverse('sessionals_index'))
    else:
        form = SessionalAccountForm(request)
    return render(request, 'sessionals/new_account.html', {'form': form})
