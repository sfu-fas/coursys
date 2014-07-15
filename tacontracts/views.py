# Django
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.db import transaction
# Local
from courselib.auth import requires_role
# App
from .models import TACategory, TAContract, TACourse
from .forms import TACategoryForm, TAContractForm, TACourseForm


def _home_redirect():
    return HttpResponseRedirect(reverse('tacontracts.views.list_all_contracts'))

def _contract_redirect(contract):
    return HttpResponseRedirect(reverse('tacontracts.views.view_contract', 
                                        kwargs={'contract_slug':contract.slug}))

@requires_role(["TAAD", "GRAD"])
def list_all_contracts(request):
    print request.units
    categories = TACategory.objects.visible(request.units)
    contracts = TAContract.objects.visible(request.units)
    return render(request, 'tacontracts/list_all_contracts.html', {
        'categories':categories, 
        'contracts':contracts
    })

@requires_role(["TAAD", "GRAD"])
def new_category(request):
    if request.method == 'POST':
        form = TACategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.save()
            messages.add_message(request, 
                                 messages.SUCCESS, 
                                 u'Category %s created.' % str(category))
            return _home_redirect()
    else:
        form = TACategoryForm()
    return render(request, 'tacontracts/new_category.html', {
                  'form':form})

@requires_role(["TAAD", "GRAD"])
def edit_category(request, category_slug):
    category = get_object_or_404(TACategory, 
                                 slug=category_slug, 
                                 account__unit__in=request.units)
    pass

@requires_role(["TAAD", "GRAD"])
def hide_category(request, category_slug):
    category = get_object_or_404(TACategory, 
                                 slug=category_slug, 
                                 account__unit__in=request.units)
    if request.method == 'POST':
        category.hide()
    pass

@requires_role(["TAAD", "GRAD"])
def new_contract(request, category_slug):
    category = get_object_or_404(TACategory, 
                                 slug=category_slug, 
                                 account__unit__in=request.units)
    if request.method == 'POST':
        form = TAContractForm(request.POST)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.category = category
            contract.save()
            messages.add_message(request, 
                                 messages.SUCCESS, 
                                 u'Contract %s created.' % str(contract))
            return _contract_redirect(contract)
    else:
        form = TAContractForm()
    return render(request, 'tacontracts/new_contract.html', {
                  'category':category,
                  'form':form})

@requires_role(["TAAD", "GRAD"])
def view_contract(request, contract_slug):
    contract = get_object_or_404(TAContract,
                                 slug=contract_slug,
                                 category__account__unit__in=request.units)
    category = contract.category
    courses = contract.course.all()
    courseform = TACourseForm()
    return render(request, 'tacontracts/view_contract.html', {
                   'editable': not contract.frozen,
                   'category': category, 
                   'contract': contract, 
                   'courseform': courseform,
                   'courses': courses })

@requires_role(["TAAD", "GRAD"])
def edit_contract(request, contract_slug):
    contract = get_object_or_404(TAContract,
                                 slug=contract_slug,
                                 category__account__unit__in=request.units)
    pass


@requires_role(["TAAD", "GRAD"])
def sign_contract(request, contract_slug):
    if request.method == "POST":
        contract = get_object_or_404(TAContract,
                                     slug=contract_slug,
                                     category__account__unit__in=request.units)
        contract.sign()
        messages.add_message(request, 
                             messages.SUCCESS, 
                             u'Contract signed!')
        return _contract_redirect(contract_slug)
    else:
        return _contract_redirect(contract_slug)

@requires_role(["TAAD", "GRAD"])
def cancel_contract(request, contract_slug):
    if request.method == "POST":
        contract = get_object_or_404(TAContract,
                                     slug=contract_slug,
                                     category__account__unit__in=request.units)
        contract.cancel()
        messages.add_message(request, 
                             messages.SUCCESS, 
                             u'Contract deleted!')
        return _home_redirect()
    else:
        return _contract_redirect(contract_slug)

@requires_role(["TAAD", "GRAD"])
@transaction.atomic
def copy_contract(request, contract_slug):
    if request.method == "POST":
        contract = get_object_or_404(TAContract,
                                     slug=contract_slug,
                                     category__account__unit__in=request.units)

        messages.add_message(request, 
                             messages.SUCCESS, 
                             u'Contract copied!')
        return _contract_redirect(newcontract_slug)
    else:
        return _contract_redirect(contract_slug)

@requires_role(["TAAD", "GRAD"])
def new_course(request, contract_slug):
    contract = get_object_or_404(TAContract,
                                 slug=contract_slug,
                                 category__account__unit__in=request.units)
    category = contract.category
    if request.method == 'POST':
        form = TACourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.contract = contract
            course.save()
            messages.add_message(request, 
                                 messages.SUCCESS, 
                                 u'Course %s created.' % str(course))
            return _contract_redirect(contract)
    else:
        form = TACourseForm()
    return render(request, 'tacontracts/new_course.html', {
                  'category':category,
                  'contract':contract,
                  'form':form})
    pass

@requires_role(["TAAD", "GRAD"])
def edit_course(request, contract_slug, course_slug):
    contract = get_object_or_404(TAContract,
                                 slug=contract_slug,
                                 category__account__unit__in=request.units)
    course = get_object_or_404(TACourse,
                                 contract=contract,
                                 slug=contract_slug,
                                 category__account__unit__in=request.units)
    pass
