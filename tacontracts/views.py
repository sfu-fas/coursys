# Python
import datetime
# Third-Party
import unicodecsv as csv
# Django
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.db import transaction, IntegrityError
from django.contrib.auth.decorators import login_required
# Local
from courselib.auth import requires_role
from coredata.models import Semester, Unit
from dashboard.models import NewsItem
# App
from .models import HiringSemester, TACategory, TAContract, TACourse, \
                    EmailReceipt
from .forms import HiringSemesterForm, TACategoryForm, TAContractForm, \
                    TACourseForm, EmailForm
from .pdfs import ta_pdf


def _home_redirect():
    return HttpResponseRedirect(reverse('tacontracts.views.list_all_semesters'))


def _contracts_redirect(semester):
    if not isinstance(semester, basestring):
        raise ValueError("Semester must be a four-character string - 1141")
    return HttpResponseRedirect(reverse('tacontracts.views.list_all_contracts', 
                                        kwargs={'semester':semester}))


def _category_redirect(semester):
    if not isinstance(semester, basestring):
        raise ValueError("Semester must be a four-character string - 1141")
    return HttpResponseRedirect(reverse('tacontracts.views.view_categories',
                                        kwargs={'semester':semester}))


def _contract_redirect(semester, contract_slug):
    if not isinstance(semester, basestring):
        raise ValueError("Semester must be a four-character string - 1141")
    return HttpResponseRedirect(reverse('tacontracts.views.view_contract',
                                        kwargs={'semester':semester, 
                                                'contract_slug':contract_slug}))


@requires_role(["TAAD", "GRAD"])
def list_all_semesters(request):
    semesters = HiringSemester.objects.visible(request.units)

    # if you have access to more than one unit, 
    # you can see more than one unit
    display_units = False
    if len(request.units) > 1:
        display_units = True

    try:
        current_semester = Semester.current()
    except Semester.DoesNotExist:
        current_semester = None
    try:
        next_semester = Semester.current().offset(1)
    except Semester.DoesNotExist:
        next_semester = None
    
    # If the user has multiple request.units, it's possible that they may
    #  have to deal with more than one HiringSemester per Semester

    if current_semester:
        current_hiring_semesters = HiringSemester.objects.semester\
                                          (current_semester.name, request.units)
    else:
        current_hiring_semesters = []

    if next_semester:
        next_hiring_semesters = HiringSemester.objects.semester\
                                             (next_semester.name, request.units)
    else:
        next_hiring_semesters = []

    return render(request, 'tacontracts/list_all_semesters.html', {
        'display_units':display_units,
        'semesters':semesters,
        'current_semester': current_semester,
        'current_hiring_semesters':current_hiring_semesters,
        'next_semester': next_semester,
        'next_hiring_semesters':next_hiring_semesters
    })


@requires_role(["TAAD", "GRAD"])
def new_semester(request):
    if request.method == 'POST':
        form = HiringSemesterForm(request, request.POST)
        if form.is_valid():
            sem = form.save(commit=False)
            sem.save()
            messages.add_message(request, 
                                 messages.SUCCESS, 
                                 u'Semester %s created.' % str(sem))
            return _contracts_redirect(sem.semester.name)
    else:
        form = HiringSemesterForm(request)


    return render(request, 'tacontracts/new_semester.html', {
                  'form':form})


@requires_role(["TAAD", "GRAD"])
def setup_semester(request, semester):
    """
    Exactly like 'new semester', but with the Semester field pre-set
    """
    semester = get_object_or_404(Semester, name=semester) 

    form = HiringSemesterForm(request, initial={
        'semester':semester,
        'pay_start':semester.start, 
        'pay_end':semester.end, 
        'payperiods': 6})
    return render(request, 'tacontracts/new_semester.html', {
                  'form':form})


@requires_role(["TAAD", "GRAD"])
def edit_semester(request, semester):
    semester = get_object_or_404(HiringSemester, 
                                 semester__name=semester, 
                                 unit__in=request.units)
    
    if request.method == 'POST':
        form = HiringSemesterForm(request, request.POST, instance=semester)
        if form.is_valid():
            sem = form.save(commit=False)
            sem.save()
            messages.add_message(request, 
                                 messages.SUCCESS, 
                                 u'Semester %s updated.' % str(sem))
            return _home_redirect()
    else:
        form = HiringSemesterForm(request, instance=semester)
    return render(request, 'tacontracts/edit_semester.html', {
                    'hiring_semester':semester,
                    'form':form})


@requires_role(["TAAD", "GRAD"])
def list_all_contracts(request, semester):
    hiring_semester = get_object_or_404(HiringSemester, 
                                        semester__name=semester, 
                                        unit__in=request.units)
    categories = TACategory.objects.visible(hiring_semester)
    contracts = TAContract.objects.visible(hiring_semester)
    draft_contracts = TAContract.objects.draft(hiring_semester)
    signed_contracts = TAContract.objects.signed(hiring_semester)
    cancelled_contracts = TAContract.objects.cancelled(hiring_semester)

    # Should we show the user the option to copy categories 
    #   from previous semester?
    show_copy_categories = True
    prev_semester = hiring_semester.semester.previous_semester()
    if not prev_semester:
        show_copy_categories = False
    else:
        try:
            prev_hiring_semester = HiringSemester.objects.get(semester=prev_semester)
        except HiringSemester.DoesNotExist:
            show_copy_categories = False

    if (('copied_categories' in hiring_semester.config and 
            hiring_semester.config['copied_categories'])):
        show_copy_categories = False

    return render(request, 'tacontracts/list_all_contracts.html', {
        'semester':semester,
        'categories':categories, 
        'contracts':contracts,
        'draft_contracts':draft_contracts,
        'signed_contracts':signed_contracts,
        'cancelled_contracts':cancelled_contracts,
        'show_copy_categories':show_copy_categories,
    })


@requires_role(["TAAD", "GRAD"])
def copy_categories(request, semester):
    hiring_semester = get_object_or_404(HiringSemester, 
                                        semester__name=semester, 
                                        unit__in=request.units)
    if ('copied_categories' in hiring_semester.config and
            hiring_semester.config['copied_categories']):
        messages.add_message(request,
                             messages.ERROR,
                             u'TA Categories have already been copied.')
    try:
        hiring_semester.copy_categories_from_previous_semester()
        hiring_semester.config['copied_categories'] = True
        messages.add_message(request, 
                             messages.SUCCESS, 
                             u'TA Categories copied.')
    except NoPreviousSemesterException:
        messages.add_message(request,
                             messages.ERROR,
                             u'No previous semester to copy from.')

    _category_redirect(hiring_semester.semester.name)


@requires_role(["TAAD", "GRAD"])
def view_categories(request, semester):
    hiring_semester = get_object_or_404(HiringSemester, 
                                        semester__name=semester, 
                                        unit__in=request.units)
    categories = TACategory.objects.visible(hiring_semester)
    return render(request, 'tacontracts/view_categories.html', {
        'semester':semester,
        'categories':categories,
        })

    
@requires_role(["TAAD", "GRAD"])
def new_category(request, semester):
    hiring_semester = get_object_or_404(HiringSemester, 
                                        semester__name=semester, 
                                        unit__in=request.units)
    if request.method == 'POST':
        form = TACategoryForm(hiring_semester.unit, request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.hiring_semester = hiring_semester
            category.save()
            messages.add_message(request, 
                                 messages.SUCCESS, 
                                 u'Category %s created.' % str(category))
            return _category_redirect(semester)
    else:
        form = TACategoryForm(hiring_semester.unit)
    return render(request, 'tacontracts/new_category.html', {
                  'semester':semester,
                  'form':form})


@requires_role(["TAAD", "GRAD"])
def edit_category(request, semester, category_slug):
    hiring_semester = get_object_or_404(HiringSemester, 
                                        semester__name=semester, 
                                        unit__in=request.units)
    category = get_object_or_404(TACategory, 
                                 slug=category_slug, 
                                 hiring_semester=hiring_semester,
                                 account__unit__in=request.units)
    if request.method == 'POST':
        form = TACategoryForm(hiring_semester.unit, request.POST, instance=category)
        if form.is_valid():
            category = form.save(commit=False)
            category.save()
            messages.add_message(request, 
                                 messages.SUCCESS, 
                                 u'Category %s updated.' % str(category))
            return _category_redirect(semester)
    else:
        form = TACategoryForm(hiring_semester.unit, instance=category)
    return render(request, 'tacontracts/edit_category.html', {
                  'semester':semester,
                  'category':category,
                  'form':form})


@requires_role(["TAAD", "GRAD"])
def hide_category(request, semester, category_slug):
    hiring_semester = get_object_or_404(HiringSemester, 
                                        semester__name=semester, 
                                        unit__in=request.units)
    category = get_object_or_404(TACategory, 
                                 slug=category_slug, 
                                 hiring_semester=hiring_semester,
                                 account__unit__in=request.units)
    if request.method == 'POST':
        category.hide()
        messages.add_message(request, 
                             messages.SUCCESS, 
                             u'Category %s hidden.' % str(category))
    return _category_redirect(semester)


@requires_role(["TAAD", "GRAD"])
def new_contract(request, semester):
    hiring_semester = get_object_or_404(HiringSemester, 
                                        semester__name=semester, 
                                        unit__in=request.units)
    if request.method == 'POST':
        form = TAContractForm(hiring_semester, request.POST)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.created_by = request.user.username
            contract.save()
            messages.add_message(request, 
                                 messages.SUCCESS, 
                                 u'Contract %s created.' % str(contract))
            return _contract_redirect(semester, contract.slug)
    else:
        form = TAContractForm(hiring_semester, initial={
            'pay_start':hiring_semester.pay_start,
            'pay_end':hiring_semester.pay_end,
            'payperiods':hiring_semester.payperiods
        })
    return render(request, 'tacontracts/new_contract.html', {
                  'semester':semester,
                  'form':form})


@requires_role(["TAAD", "GRAD"])
def view_contract(request, semester, contract_slug):
    hiring_semester = get_object_or_404(HiringSemester, 
                                        semester__name=semester, 
                                        unit__in=request.units)
    contract = get_object_or_404(TAContract,
                                 category__hiring_semester=hiring_semester,
                                 slug=contract_slug,
                                 category__account__unit__in=request.units)
    category = contract.category
    courses = contract.course.all()
    emails = contract.email_receipt.all()
    courseform = TACourseForm(semester)
    return render(request, 'tacontracts/view_contract.html', {
                   'semester': semester,
                   'editable': not contract.frozen,
                   'category': category, 
                   'contract': contract, 
                   'courseform': courseform,
                   'emails': emails,
                   'courses': courses })


@requires_role(["TAAD", "GRAD"])
def edit_contract(request, semester, contract_slug):
    hiring_semester = get_object_or_404(HiringSemester, 
                                        semester__name=semester, 
                                        unit__in=request.units)
    contract = get_object_or_404(TAContract,
                                 category__hiring_semester=hiring_semester,
                                 slug=contract_slug,
                                 category__account__unit__in=request.units)
    if request.method == 'POST':
        form = TAContractForm(hiring_semester, request.POST, instance=contract)
        if form.is_valid():
            contract = form.save()
            messages.add_message(request, 
                                 messages.SUCCESS, 
                                 u'Contract %s updated.' % str(contract))
            return _contract_redirect(semester, contract.slug)
    else:
        form = TAContractForm(hiring_semester, instance=contract)
    return render(request, 'tacontracts/edit_contract.html', {
                  'semester':semester,
                  'category':contract.category,
                  'contract':contract,
                  'form':form})


@requires_role(["TAAD", "GRAD"])
def sign_contract(request, semester, contract_slug):
    if request.method == "POST":
        hiring_semester = get_object_or_404(HiringSemester, 
                                            semester__name=semester, 
                                            unit__in=request.units)
        contract = get_object_or_404(TAContract,
                                     category__hiring_semester=hiring_semester,
                                     slug=contract_slug,
                                     category__account__unit__in=request.units)
        contract.sign()
        messages.add_message(request, 
                             messages.SUCCESS, 
                             u'Contract signed!')
        return _contract_redirect(semester, contract_slug)
    else:
        return _contract_redirect(semester, contract_slug)


@requires_role(["TAAD", "GRAD"])
def cancel_contract(request, semester, contract_slug):
    if request.method == "POST":
        hiring_semester = get_object_or_404(HiringSemester, 
                                            semester__name=semester, 
                                            unit__in=request.units)
        contract = get_object_or_404(TAContract,
                                     category__hiring_semester=hiring_semester,
                                     slug=contract_slug,
                                     category__account__unit__in=request.units)
        if contract.status == "NEW":
            contract.cancel()
            messages.add_message(request, 
                                 messages.SUCCESS, 
                                 u'Contract Deleted!')
            return _contracts_redirect(semester)
        else:
            contract.cancel()
            messages.add_message(request, 
                                 messages.SUCCESS,
                                 u'Contract Cancelled!')
            return _contract_redirect(semester, contract.slug)
    else:
        return _contract_redirect(semester, contract_slug)


@requires_role(["TAAD", "GRAD"])
@transaction.atomic
def copy_contract(request, semester, contract_slug):
    if request.method == "POST":
        hiring_semester = get_object_or_404(HiringSemester, 
                                            semester__name=semester, 
                                            unit__in=request.units)
        contract = get_object_or_404(TAContract,
                                     category__hiring_semester=hiring_semester,
                                     slug=contract_slug,
                                     category__account__unit__in=request.units)
        newcontract = contract.copy(request.user.username)
        messages.add_message(request, 
                             messages.SUCCESS, 
                             u'Contract copied!')
        return _contract_redirect(semester, newcontract.slug)
    else:
        return _contract_redirect(semester, contract_slug)


@requires_role(["TAAD", "GRAD"])
def print_contract(request, semester, contract_slug):
    hiring_semester = get_object_or_404(HiringSemester, 
                                        semester__name=semester, 
                                        unit__in=request.units)
    contract = get_object_or_404(TAContract,
                                 category__hiring_semester=hiring_semester,
                                 slug=contract_slug,
                                 category__account__unit__in=request.units)
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename="%s-%s.pdf"' % \
                                        (contract.slug, contract.person.userid)
    ta_pdf(contract, response)
    return response


@requires_role(["TAAD", "GRAD"])
def new_course(request, semester, contract_slug):
    hiring_semester = get_object_or_404(HiringSemester, 
                                        semester__name=semester, 
                                        unit__in=request.units)
    contract = get_object_or_404(TAContract,
                                 category__hiring_semester=hiring_semester,
                                 slug=contract_slug,
                                 category__account__unit__in=request.units)
    category = contract.category
    if request.method == 'POST':
        form = TACourseForm(semester, request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.contract = contract
            try:
                course.save()
            except IntegrityError:
                messages.add_message(request, 
                                     messages.ERROR, 
                                     u'This contract already has %s.' % str(course))
                return _contract_redirect(semester, contract.slug)
            messages.add_message(request, 
                                 messages.SUCCESS, 
                                 u'Course %s created.' % str(course))
            return _contract_redirect(semester, contract.slug)
    else:
        form = TACourseForm(semester)
    return render(request, 'tacontracts/new_course.html', {
                  'semester':semester,
                  'category':category,
                  'contract':contract,
                  'form':form})


@requires_role(["TAAD", "GRAD"])
def delete_course(request, semester, contract_slug, course_slug):
    if request.method == 'POST':
        hiring_semester = get_object_or_404(HiringSemester, 
                                            semester__name=semester, 
                                            unit__in=request.units)
        contract = get_object_or_404(TAContract,
                                     category__hiring_semester=hiring_semester,
                                     slug=contract_slug,
                                     category__account__unit__in=request.units)
        course = get_object_or_404(TACourse,
                                     contract=contract,
                                     slug=course_slug)
        course.delete()
        messages.add_message(request, messages.SUCCESS, u'Course deleted.')
        return _contract_redirect(semester, contract_slug)
    else:
        return _contract_redirect(semester, contract_slug)


@requires_role(["TAAD", "GRAD"])
def bulk_email(request, semester):
    hiring_semester = get_object_or_404(HiringSemester, 
                                        semester__name=semester, 
                                        unit__in=request.units)
    contracts = TAContract.objects.draft(hiring_semester)
    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            sender = form.cleaned_data['sender']
            url = reverse('tacontracts.views.student_contract', 
                                                  kwargs={'semester':semester})
            contract_ids = [int(x) for x in request.POST.getlist('contracts[]')]
            contracts = TAContract.objects.visible(hiring_semester)\
                                          .filter(id__in=contract_ids)
            for contract in contracts:
                n = NewsItem(user=contract.person, 
                             source_app="tacontracts", 
                             title=subject,
                             url=url, 
                             author=sender, 
                             content=message)
                n.save()
                e = EmailReceipt(contract=contract, 
                                 content=subject + "\n\n" + message)
                e.save()
            messages.add_message(request, messages.SUCCESS, u'Email sent.')
            return _contracts_redirect(semester)
    else:
        form = EmailForm()
    return render(request, 'tacontracts/bulk_email.html', {
                  'semester':semester,
                  'contracts':contracts,
                  'form':form,
                  })


@login_required
def student_contract(request, semester):
    contracts = TAContract.objects.filter(category__hiring_semester__semester__name=semester, 
                                          status__in=["NEW", "SGN"],
                                          person__userid=request.user.username) 
    return render(request, 'tacontracts/student_contract.html', {
                  'semester':semester,
                  'contracts':contracts,
                  })

@login_required
def accept_contract(request, semester, contract_slug):
    contract = get_object_or_404(TAContract,
                                          category__hiring_semester__semester__name=semester, 
                                          person__userid=request.user.username, 
                                          slug=contract_slug) 
    if request.POST:
        contract.accepted_by_student = True
        contract.save()
        messages.add_message(request, 
                             messages.SUCCESS, 
                             u'Contract Accepted.')
    return HttpResponseRedirect(reverse('tacontracts.views.student_contract', 
                                        kwargs={'semester':semester}))


@requires_role(["TAAD", "GRAD"])
def contracts_csv(request, semester):
    hiring_semester = get_object_or_404(HiringSemester, 
                                        semester__name=semester, 
                                        unit__in=request.units)

    contracts = TAContract.objects.signed(hiring_semester)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'inline; filename="%s.csv"' % (hiring_semester.semester.name)
    writer = csv.writer(response)
    writer.writerow(['Batch ID', 'Term ID', 'Contract Signed', 
                     'Benefits Indicator', 'EmplID', 'SIN',
                     'Last Name', 'First Name 1', 'First Name 2', 
                     'Payroll Start Date', 'Payroll End Date',
                     'Action', 'Action Reason', 'Position Number', 
                     'Job Code', 'Full_Part time', 'Pay Group',
                     'Employee Class', 'Category', 'Fund', 
                     'Dept ID (cost center)', 'Project', 'Account',
                     'Prep Units', 'Base Units', 'Appt Comp Freq', 
                     'Semester Base Salary Rate',
                     'Biweekly Base Salary Pay Rate', 
                     'Hourly Rate', 'Standard Hours', 'Scholarship Rate Code',
                     'Semester Scholarship Salary Pay Rate', 
                     'Biweekly Scholarship Salary Pay Rate', 'Lump Sum Amount',
                     'Lump Sum Hours', 'Scholarship Lump Sum'])
    
    seq = hiring_semester.next_export_seq()
    batchid = '%s_%s_%02i' % (hiring_semester.unit.label, 
                              datetime.date.today().strftime("%Y%m%d"), seq)

    for c in contracts:
        bu = c.bu
        total_bu = c.total_bu
        prep_units = c.total_bu - c.bu
        
        signed = 'Y'
        benefits = 'Y'
        schol_rate = 'TSCH' if c.scholarship_per_bu > 0 else ''
        salary_total = c.total_pay 
        schol_total = c.scholarship_pay
        if prep_units == 0:
            prep_units = ''
        
        row = []
        #Batch ID
        row.append(batchid)
        #Term ID
        row.append(hiring_semester.semester.name)
        #Signed
        row.append(signed)
        #Benefits Indicator
        row.append(benefits)
        #Emplid
        row.append(c.person.emplid)
        #SIN
        row.append(c.sin)
        #Name
        row.extend([c.person.last_name, 
                    c.person.first_name, 
                    c.person.middle_name])
        #Payroll Start Date, Payroll End Date
        row.append(c.pay_start.strftime("%Y%m%d"))
        row.append(c.pay_end.strftime("%Y%m%d"))
        #Action, Action Reason
        row.append('REH')
        row.append('REH')
        #Position Number
        row.append("%08i" % c.category.account.position_number)
        #Job Code
        row.append('')
        #Full_Part time
        row.append('')
        #Pay Group
        row.append('TSU')
        #Employee Class
        row.append('')
        #Category
        row.append(c.category.code)
        #Fund
        row.append(11)
        #Dept ID(cost center)
        row.append(hiring_semester.unit.deptid())
        #Project
        row.append('')
        #Account
        row.append(c.category.account.account_number)
        #Prep Units
        row.append(prep_units)
        #Base Units
        row.append(bu)
        #Appt Comp Freq
        row.append('T')
        #Semester Base Salary Rate
        row.append("%2f"%(salary_total,))
        #Biweekly Base Salary Rate, Hourly Rate, Standard Hours
        row.extend(['','',''])
        #Scholarhip Rate Code
        row.append(schol_rate)
        #Semester Scholarship Salary Pay Rate
        row.append(schol_total)
        #Biweekly Scholarship Salary Pay Rate, Lump Sum Amount
        #Lump Sum Hours, Scholarship Lump Sum
        row.extend(['','','',''])

        writer.writerow(row)
    
    return response
