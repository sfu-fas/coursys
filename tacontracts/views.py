# Django
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.db import transaction, IntegrityError
# Local
from courselib.auth import requires_role
# App
from .models import TACategory, TAContract, TACourse
from .forms import TACategoryForm, TAContractForm, TACourseForm
from .pdfs import ta_pdf


def _home_redirect():
    return HttpResponseRedirect(reverse('tacontracts.views.list_all_contracts'))

def _category_redirect():
    return HttpResponseRedirect(reverse('tacontracts.views.view_categories'))

def _contract_redirect(contract_slug):
    return HttpResponseRedirect(reverse('tacontracts.views.view_contract', 
                                        kwargs={'contract_slug':contract_slug}))

@requires_role(["TAAD", "GRAD"])
def list_all_contracts(request):
    categories = TACategory.objects.visible(request.units)
    contracts = TAContract.objects.visible(request.units)
    draft_contracts = TAContract.objects.draft(request.units)
    signed_contracts = TAContract.objects.signed(request.units)
    cancelled_contracts = TAContract.objects.cancelled(request.units)
    return render(request, 'tacontracts/list_all_contracts.html', {
        'categories':categories, 
        'contracts':contracts,
        'draft_contracts':draft_contracts,
        'signed_contracts':signed_contracts,
        'cancelled_contracts':cancelled_contracts
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
            return _category_redirect()
    else:
        form = TACategoryForm()
    return render(request, 'tacontracts/new_category.html', {
                  'form':form})

@requires_role(["TAAD", "GRAD"])
def view_categories(request):
    categories = TACategory.objects.visible(request.units)
    return render(request, 'tacontracts/view_categories.html', {
        'categories':categories,
        })

@requires_role(["TAAD", "GRAD"])
def edit_category(request, category_slug):
    category = get_object_or_404(TACategory, 
                                 slug=category_slug, 
                                 account__unit__in=request.units)
    if request.method == 'POST':
        form = TACategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save(commit=False)
            category.save()
            messages.add_message(request, 
                                 messages.SUCCESS, 
                                 u'Category %s updated.' % str(category))
            return _category_redirect()
    else:
        form = TACategoryForm(instance=category)
    return render(request, 'tacontracts/edit_category.html', {
                  'category':category,
                  'form':form})

@requires_role(["TAAD", "GRAD"])
def hide_category(request, category_slug):
    category = get_object_or_404(TACategory, 
                                 slug=category_slug, 
                                 account__unit__in=request.units)
    if request.method == 'POST':
        category.hide()
    return _category_redirect()

@requires_role(["TAAD", "GRAD"])
def new_contract(request):
    if request.method == 'POST':
        form = TAContractForm(request.POST, units=request.units)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.created_by = request.user.username
            contract.save()
            messages.add_message(request, 
                                 messages.SUCCESS, 
                                 u'Contract %s created.' % str(contract))
            return _contract_redirect(contract.slug)
    else:
        form = TAContractForm(units=request.units)
    return render(request, 'tacontracts/new_contract.html', {
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
    if request.method == 'POST':
        form = TAContractForm(request.POST, instance=contract, units=request.units)
        if form.is_valid():
            contract = form.save()
            messages.add_message(request, 
                                 messages.SUCCESS, 
                                 u'Contract %s updated.' % str(contract))
            return _contract_redirect(contract.slug)
    else:
        form = TAContractForm(instance=contract, units=request.units)
    return render(request, 'tacontracts/edit_contract.html', {
                  'category':contract.category,
                  'contract':contract,
                  'form':form})


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
        if contract.status == "NEW":
            contract.cancel()
            messages.add_message(request, 
                                 messages.SUCCESS, 
                                 u'Contract Deleted!')
            return _home_redirect()
        else:
            contract.cancel()
            messages.add_message(request, 
                                 messages.SUCCESS,
                                 u'Contract Cancelled!')
            return _contract_redirect(contract.slug)
    else:
        return _contract_redirect(contract_slug)

@requires_role(["TAAD", "GRAD"])
@transaction.atomic
def copy_contract(request, contract_slug):
    if request.method == "POST":
        contract = get_object_or_404(TAContract,
                                     slug=contract_slug,
                                     category__account__unit__in=request.units)
        newcontract = contract.copy(request.user.username)
        messages.add_message(request, 
                             messages.SUCCESS, 
                             u'Contract copied!')
        return _contract_redirect(newcontract.slug)
    else:
        return _contract_redirect(contract_slug)

@requires_role(["TAAD", "GRAD"])
def print_contract(request, contract_slug):
    contract = get_object_or_404(TAContract,
                                 slug=contract_slug,
                                 category__account__unit__in=request.units)
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename="%s-%s.pdf"' % \
                                        (contract.slug, contract.person.userid)
    ta_pdf(contract, response)
    return response

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
            try:
                course.save()
            except IntegrityError:
                messages.add_message(request, 
                                     messages.ERROR, 
                                     u'This contract already has %s.' % str(course))
                return _contract_redirect(contract.slug)
            messages.add_message(request, 
                                 messages.SUCCESS, 
                                 u'Course %s created.' % str(course))
            return _contract_redirect(contract.slug)
    else:
        form = TACourseForm()
    return render(request, 'tacontracts/new_course.html', {
                  'category':category,
                  'contract':contract,
                  'form':form})

@requires_role(["TAAD", "GRAD"])
def delete_course(request, contract_slug, course_slug):
    if request.method == 'POST':
        contract = get_object_or_404(TAContract,
                                     slug=contract_slug,
                                     category__account__unit__in=request.units)
        course = get_object_or_404(TACourse,
                                     contract=contract,
                                     slug=course_slug)
        course.delete()
        messages.add_message(request, messages.SUCCESS, u'Course deleted.')
        return _contract_redirect(contract_slug)
    else:
        return _contract_redirect(contract_slug)
