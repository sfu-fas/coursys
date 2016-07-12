from courselib.auth import requires_role
from .models import SessionalAccount, SessionalContract, SessionalConfig
from .forms import SessionalAccountForm, SessionalContractForm, SessionalConfigForm
from django.shortcuts import render, HttpResponseRedirect, get_object_or_404, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib import messages
from log.models import LogEntry
from courselib.auth import ForbiddenResponse
from datetime import datetime
from courselib.search import find_userid_or_emplid
from coredata.models import AnyPerson, Role

def _has_unit_role(user, account_or_contract):
    """
    A quick method to check that the person has a sessional Admin role for the given unit.  Since both SessionalAccounts
    and SessionalContracts have a unit attribute, we can just use this same method for both.
    """
    sessional_admin_roles=["TAAD", "GRAD", "ADMN"]
    return Role.objects.filter(person__userid=user.username, role__in=sessional_admin_roles,
                               unit=account_or_contract.unit).count() > 0

@requires_role(["TAAD", "GRAD", "ADMN"])
def sessionals_index(request):
    return render(request, 'sessionals/index.html')


@requires_role(["TAAD", "GRAD", "ADMN"])
def manage_accounts(request):
    accounts = SessionalAccount.objects.visible(request.units)
    return render(request, 'sessionals/manage_accounts.html', {'accounts': accounts})


@requires_role(["TAAD", "GRAD", "ADMN"])
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
                         description="added account: %s" % account,
                         related_object=account
                         )
            l.save()

            return HttpResponseRedirect(reverse('sessionals:manage_accounts'))
    else:
        form = SessionalAccountForm(request)
    return render(request, 'sessionals/new_account.html', {'form': form})


@requires_role(["TAAD", "GRAD", "ADMN"])
def edit_account(request, account_slug):
    account = get_object_or_404(SessionalAccount, slug=account_slug)
    if not _has_unit_role(request.user, account):
        return ForbiddenResponse(request)
    if request.method == 'POST':
        form = SessionalAccountForm(request, request.POST, instance=account)
        if form.is_valid():
            account = form.save(commit=False)
            account.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Account was edited.'
                                 )
            l = LogEntry(userid=request.user.username,
                         description="edited account: %s" % account,
                         related_object=account
                         )
            l.save()
            return HttpResponseRedirect(reverse('sessionals:manage_accounts'))
    else:
        form = SessionalAccountForm(request, instance=account)
    return render(request, 'sessionals/edit_account.html', {'form': form, 'account': account})


@requires_role(["TAAD", "GRAD", "ADMN"])
def delete_account(request, account_id):
    account = get_object_or_404(SessionalAccount, id=account_id)
    if not _has_unit_role(request.user, account):
        return ForbiddenResponse(request)
    if request.method == 'POST':
        account.delete()
        messages.add_message(request,
                             messages.SUCCESS,
                             u'Account was deleted.'
                             )
        l = LogEntry(userid=request.user.username,
                     description="deleted account: %s" % account,
                     related_object=account
                     )
        l.save()
    return HttpResponseRedirect(reverse('sessionals:manage_accounts'))


@requires_role(["TAAD", "GRAD", "ADMN"])
def view_account(request, account_slug):
    account = get_object_or_404(SessionalAccount, slug=account_slug)
    if not _has_unit_role(request.user, account):
        return ForbiddenResponse(request)
    return render(request, 'sessionals/view_account.html', {'account': account})


@requires_role(["TAAD", "GRAD", "ADMN"])
def manage_configs(request):
    configs = SessionalConfig.objects.filter(unit__in=request.units)
    #  Sysadmins may manage multiple units.  We'll make sure they always see the "new config" action.  Others
    #  presumably all only admin one single unit, so should only see that link if they don't already have a default
    #  config, since it has a one-to-one relationship with the unit.
    is_admin = Role.objects.filter(person__userid=request.user.username, role='SYSA').count() > 0
    return render(request, 'sessionals/manage_configs.html', {'configs': configs, 'is_admin': is_admin})


@requires_role(["TAAD", "GRAD", "ADMN"])
def new_config(request):
    if request.method == 'POST':
        form = SessionalConfigForm(request, request.POST)
        if form.is_valid():
            config = form.save(commit=False)
            config.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Configuration was created.'
                                 )
            l = LogEntry(userid=request.user.username,
                         description="added config: %s" % config,
                         related_object=config
                         )
            l.save()

            return HttpResponseRedirect(reverse('sessionals:manage_configs'))
    else:
        form = SessionalConfigForm(request)
    return render(request, 'sessionals/new_config.html', {'form': form})


@requires_role(["TAAD", "GRAD", "ADMN"])
def edit_config(request, config_slug):
    config = get_object_or_404(SessionalConfig, slug=config_slug)
    if not _has_unit_role(request.user, config):
        return ForbiddenResponse(request)
    if request.method == 'POST':
        form = SessionalConfigForm(request, request.POST, instance=config)
        if form.is_valid():
            config = form.save(commit=False)
            config.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Configuration was edited.'
                                 )
            l = LogEntry(userid=request.user.username,
                         description="edited config: %s" % config,
                         related_object=config
                         )
            l.save()
            return HttpResponseRedirect(reverse('sessionals:manage_configs'))
    else:
        form = SessionalConfigForm(request, instance=config)
    return render(request, 'sessionals/edit_config.html', {'form': form, 'config': config})
