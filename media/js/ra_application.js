var noIdFields = ['intro-first_name', 'intro-last_name', 'intro-email_address']
var idFields = ['intro-person']

var studentFields = ['intro-coop', 'intro-thesis', 'intro-research', 'intro-usra']

var fs1MultiFields = ['funding_sources-fs1_start_date', 'funding_sources-fs1_end_date', 'funding_sources-fs1_amount']

var rabw_fields = ['research_assistant-total_gross', 'research_assistant-weeks_vacation', 'research_assistant-biweekly_hours']
var rah_fields = ['research_assistant-gross_hourly', 'research_assistant-vacation_pay', 'research_assistant-biweekly_hours']
var ncbw_fields = ['non_continuing-total_gross', 'non_continuing-weeks_vacation', 'non_continuing-biweekly_hours']
var nch_fields = ['non_continuing-gross_hourly', 'non_continuing-vacation_pay', 'non_continuing-biweekly_hours']
var grasls_fields = ['graduate_research_assistant-total_gross']
var grasbw_fields = ['graduate_research_assistant-total_gross']

var ra_backdated_fields = ['research_assistant-backdate_hours', 'research_assistant-backdate_lump_sum', 'research_assistant-backdate_reason']
var nc_backdated_fields = ['non_continuing-backdate_hours', 'non_continuing-backdate_lump_sum', 'non_continuing-backdate_reason']
var gras_backdated_fields = ['graduate_research_assistant-backdate_hours', 'graduate_research_assistant-backdate_lump_sum', 'graduate_research_assistant-backdate_reason']

function hideInput (field) {
    $('label[for=id_' + field + '_0]').parent().hide()
    $('label[for=id_' + field + ']').parent().hide()
    $('#id_' + field).parent().parent().hide()
}
function showInput (field) {
    $('label[for=id_' + field + '_0]').parent().show()
    $('label[for=id_' + field + ']').parent().show()
    $('#id_' + field).parent().parent().show()
}

// hide multiple fields at a time
function hide (fields) {
    for (let i = 0; i < fields.length; i++) {
        hideInput(fields[i])
    }
}

// show multiple fields at a time
function show (fields) {
    for (let i = 0; i < fields.length; i++) {
        showInput(fields[i])
    }
}

// set radio select fields to a certain value (usually for setting to None)
function setToNone (fields) {
    for (let i = 0; i < fields.length; i++) {
        var checked = $('input[name=' + fields[i] + ']:checked')
        checked.val(['None'])
    }
}

// SECTION 1: Appointee/Supervisor Information and Hiring Category

// field change for applicants with ids vs no ids
function idFieldsUpdate () {
    if ($('#id_intro-nonstudent').is(':checked')) {
        show(noIdFields)
        hide(idFields)
    } else {
        hide(noIdFields)
        show(idFields)
    }
}

function studentFieldsUpdate () {
    var student_checked = $('input[name=intro-student]').is(':checked')
    var student = $('input[name=intro-student]:checked')
    var usra = $('input[name=intro-usra]:checked')
    if (student.val() != 'N' && student_checked === true) {
        show(['intro-coop'])
        if (student.val() == 'U') {
            show(['intro-usra'])
            if (usra.val() === 'False') {
                show(['intro-research'])
            } else {
                hide(['intro-research', 'intro-thesis'])
                setToNone(['intro-research', 'intro-thesis'])
            }
        } else if (student.val() == 'M' || student.val() == 'P') {
            show(['intro-research'])
            hide(['intro-usra'])
            setToNone(['intro-usra'])
        }
        var research = $('input[name=intro-research]:checked')
        if (research.val() === 'True') {
            show(['intro-thesis'])
        } else {
            hide(['intro-thesis'])
            setToNone(['intro-thesis'])
        }
    } else if (student.val() == 'N' && student_checked == true) {
        show(['intro-research'])
        hide(['intro-coop', 'intro-usra', 'intro-thesis'])
        setToNone(['intro-coop', 'intro-usra', 'intro-thesis'])
    } else {
        hide(studentFields)
        setToNone(studentFields)
    }
}

function researchAssistant () {
    var usra =  $('input[name=intro-usra]:checked')
    $('#id_intro-hiring_category').val('RA')
    $('.need_more_info').hide()
    $('.gras_info').hide()
    $('.nc_info').hide()
    if (usra.val() === 'True') {
        $('.usra_info').show() 
        $('.ra_info').hide()  
    } else {
        $('.usra_info').hide()
        $('.ra_info').show()
    }
}

function graduateResearchAssistant () {
    $('#id_intro-hiring_category').val('GRAS')

    $('.need_more_info').hide()
    $('.gras_info').show()
    $('.ra_info').hide()
    $('.usra_info').hide()
    $('.nc_info').hide()
}

function nonContinuing () {
    $('#id_intro-hiring_category').val('NC')

    $('.need_more_info').hide()
    $('.nc_info').show()
    $('.ra_info').hide()
    $('.usra_info').hide()
    $('.gras_info').hide()
}

function hiringCategoryRec () {
    var student = $('input[name=intro-student]:checked')
    var thesis = $('input[name=intro-thesis]:checked')
    var research =  $('input[name=intro-research]:checked')
    var usra =  $('input[name=intro-usra]:checked')
    
    if (student.val() === 'N' & research.val() === 'True') {   
        researchAssistant()
    } else if (student.val() === 'N' & research.val() === 'False') {
        nonContinuing()
    } else if (usra.val() === 'True' & student.val() === 'U') {
        researchAssistant()
    } else if (research.val() === 'False') {
        nonContinuing()
    } else if (thesis.val() == 'True') {
        graduateResearchAssistant()
    } else if (thesis.val() == 'False') {
        researchAssistant()
    } else {
        $('#id_intro-hiring_category').val('None')
        $('.need_more_info').show()
        $('.ra_info').hide()
        $('.nc_info').hide()
        $('.gras_info').hide()
        $('.usra_info').hide()
    }
}

// SECTION 2: Appointment Start and End Dates

// calculating pay periods for their info
// finds number of days between dates not including saturday & sunday, and divides by 10
// https://www.sunzala.com/why-the-javascript-date-is-one-day-off/
// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date/getTimezoneOffset
function guessPayPeriods (start_date, end_date) {
    date_1 = new Date (start_date)
    date_2 = new Date (end_date)
    date_1 = new Date(date_1.getTime() + date_1.getTimezoneOffset() * 60000)
    date_2 = new Date(date_2.getTime() + date_2.getTimezoneOffset() * 60000)

    let workingDays = 0

    while (date_1 <= date_2) {
        if (date_1.getDay() !== 0 && date_1.getDay() !== 6) {
            workingDays++;
        }
        date_1.setDate(date_1.getDate() + 1)
    }
    if (workingDays > 0) {
        diff = (Math.abs(workingDays))/(10)
        payPeriods = diff.toFixed(1)
    }
    else {
        payPeriods = 0
    }
    return payPeriods
}

function updatePayPeriods () {
    var payPeriods = guessPayPeriods($('#id_dates-start_date').val(), $('#id_dates-end_date').val())
    $('#id_dates-pay_periods').val(payPeriods)
    $('.pay_periods_info').text(payPeriods)
}

function getBackDated (end_date) {
    today = new Date ()
    today.setHours(0,0,0,0)

    date = new Date (end_date)
    date = new Date(date.getTime() + date.getTimezoneOffset() * 60000)
    date.setHours(0,0,0,0)

    if (date < today) {
        return true
    } else {
        return false
    }
}

function updateBackDated () {
    var backDated = getBackDated($('#id_dates-end_date').val())
    $('#id_dates-backdated').val(backDated)
    if (backDated == true) {
        $("#id_dates-backdated").prop("checked", true);
    } else {
        $("#id_dates-backdated").prop("checked", false);
    }
}

function updateBackDatedInfo () {
    var backDated = getBackDated($('#id_dates-end_date').val())
    if (backDated == true) {
        $('.backdated_info').show()
    } else {
        $('.backdated_info').hide()
    }
}

// SECTION 3: Funding Sources
function fs2ChoiceUpdate () {
    if ($('#id_funding_sources-fs2_option').is(':checked')) {
        $('.fs2').show()
        $('.multiple_funding_sources').show()
        show(fs1MultiFields)
    } else {
        $('.fs2').hide()
        $('.fs3').hide()
        $('.multiple_funding_sources').hide()
        hide(fs1MultiFields)
        $("#id_funding_sources-fs3_option").prop("checked", false);
    }
}

function fs3ChoiceUpdate() {
    if ($('#id_funding_sources-fs3_option').is(':checked')) {
        $('.fs3').show()
    } else {
        $('.fs3').hide()
    }
}

// SECTION 4: Payment Methods
function raPaymentMethod() {
    var raPaymentMethod = $('input[name=research_assistant-ra_payment_method]:checked')

    if (raPaymentMethod.val() === 'H') {
        $('.biweekly_info').hide()
        hide(rabw_fields)
        show(rah_fields)
        raH()
    } else if (raPaymentMethod.val() === 'BW') {
        $('.biweekly_info').show()
        hide(rah_fields)
        show(rabw_fields)
        raBW()
    } else {
        hide(rah_fields)
        hide(rabw_fields)
    }
}

function ncPaymentMethod() {
    var ncPaymentMethod = $('input[name=non_continuing-nc_payment_method]:checked')
    if (ncPaymentMethod.val() === 'H') {
        $('.biweekly_info').hide()
        hide(ncbw_fields)
        show(nch_fields)
        ncH()
    } else if (ncPaymentMethod.val() === 'BW') {
        $('.biweekly_info').show()
        hide(nch_fields)
        show(ncbw_fields)
        ncBW()
    } else {
        hide(nch_fields)
        hide(ncbw_fields)
    }
}

function grasPaymentMethod () {
    var grasPaymentMethod = $('input[name=graduate_research_assistant-gras_payment_method]:checked')
    if (grasPaymentMethod.val() === 'LE') {
        $('.biweekly_info').hide()
        hide(grasbw_fields)
        show(grasls_fields)
        grasLS()
    } else if (grasPaymentMethod.val() === 'BW') {
        $('.biweekly_info').show()
        hide(grasls_fields)
        show(grasbw_fields)
        grasBW()
    } else {
        hide(grasbw_fields)
        hide(grasls_fields)
    }
}

function grasBW () {
    totalPay = $('#id_graduate_research_assistant-total_gross').val()
    payPeriods = $('#id_graduate_research_assistant-pay_periods').val()
    if (payPeriods != 0) {
        biweeklySalary = totalPay/payPeriods
    } else {
        biweeklySalary = 0
    }
    
    biweeklySalary = biweeklySalary.toFixed(2)

    if (totalPay == '') {
        totalPay = parseInt(0).toFixed(2)
    }
    totalPay = parseFloat(totalPay).toFixed(2)
    $('#id_graduate_research_assistant-biweekly_salary').val(biweeklySalary)
    $('.biweekly_rate_info').text(biweeklySalary)
    $('.biweekly_rate_calc').text('Total Pay (' + totalPay + ') / Pay Periods (' + payPeriods + ')')
    $('#id_graduate_research_assistant-total_pay').val(totalPay)
    $('.total_pay_info').text(totalPay)
    $('.total_pay_calc').text('Total Gross (' + totalPay + ')')
}

function grasLS () {
    totalPay = $('#id_graduate_research_assistant-total_gross').val()
    if (totalPay == '') {
        totalPay = parseInt(0).toFixed(2)
    } 
    totalPay = parseFloat(totalPay).toFixed(2)
    $('#id_graduate_research_assistant-total_pay').val(totalPay)
    $('.total_pay_info').text(totalPay)
    $('.total_pay_calc').text('Total Gross (' + totalPay + ')')
}

function raBW () {
    totalPay = $('#id_research_assistant-total_gross').val()
    biweeklyHours = $('#id_research_assistant-biweekly_hours').val()
    weeksVacation = $('#id_research_assistant-weeks_vacation').val()
    payPeriods = $('#id_research_assistant-pay_periods').val()
    if (payPeriods != 0) {
        biweeklySalary = totalPay/payPeriods
    } else {
        biweeklySalary = 0
    }
    if (biweeklyHours != 0) {
        hourlyRate = biweeklySalary/biweeklyHours
    } else {
        hourlyRate = 0
    }
    vacationHours = payPeriods * (weeksVacation / 52.14) * biweeklyHours

    vacationHours = vacationHours.toFixed(2)
    biweeklySalary = biweeklySalary.toFixed(2)
    hourlyRate = hourlyRate.toFixed(2)
    if (totalPay == '') {
        totalPay = parseInt(0).toFixed(2)
    }
    totalPay = parseFloat(totalPay).toFixed(2)
    $('#id_research_assistant-biweekly_salary').val(biweeklySalary)
    $('.biweekly_rate_info').text(biweeklySalary)
    $('.biweekly_rate_calc').text('Total Pay (' + totalPay + ') / Pay Periods (' + payPeriods + ')')
    $('#id_research_assistant-vacation_hours').val(vacationHours)
    $('.vacation_hours_info').text(vacationHours)
    $('.vacation_hours_calc').text('Pay Periods (' + payPeriods + ') x (Weeks Vacation (' + weeksVacation + ') / 52.14) x Bi-Weekly Hours (' + biweeklyHours + ')')
    $('#id_research_assistant-gross_hourly').val(hourlyRate)
    $('.hourly_rate_info').text(hourlyRate)
    $('.hourly_rate_calc').text('Bi-Weekly Rate (' + biweeklySalary + ') / Bi-Weekly Hours (' + biweeklyHours + ')')
    $('#id_research_assistant-total_pay').val(totalPay)
    $('.total_pay_info').text(totalPay)
    $('.total_pay_calc').text('Total Gross (' + totalPay + ')')
}

function raH () {
    biweeklyHours = $('#id_research_assistant-biweekly_hours').val()
    hourlyRate = $('#id_research_assistant-gross_hourly').val()
    vacationPay = $('#id_research_assistant-vacation_pay').val()
    payPeriods = $('#id_research_assistant-pay_periods').val()
    totalPay = (payPeriods * biweeklyHours * hourlyRate) * (1 + (vacationPay/100))
    totalPay = totalPay.toFixed(2)
    $('#id_research_assistant-total_pay').val(totalPay)
    $('.total_pay_info').text(totalPay)
    $('.total_pay_calc').text('Pay Periods (' + payPeriods + ') x Bi-Weekly Hours (' + biweeklyHours + ') x Hourly Rate (' + hourlyRate + ') x (1 + (Vacation Pay (' + vacationPay + ')/100))')
}

function ncBW () {
    totalPay = $('#id_non_continuing-total_gross').val()
    biweeklyHours = $('#id_non_continuing-biweekly_hours').val()
    weeksVacation = $('#id_non_continuing-weeks_vacation').val()
    payPeriods = $('#id_non_continuing-pay_periods').val()
    if (payPeriods != 0) {
        biweeklySalary = totalPay/payPeriods
    } else {
        biweeklySalary = 0
    }
    if (biweeklyHours != 0) {
        hourlyRate = biweeklySalary/biweeklyHours
    } else {
        hourlyRate = 0
    }
    vacationHours = payPeriods * (weeksVacation / 52.14) * biweeklyHours

    vacationHours = vacationHours.toFixed(2)
    biweeklySalary = biweeklySalary.toFixed(2)
    hourlyRate = hourlyRate.toFixed(2)
    if (totalPay == '') {
        totalPay = parseInt(0).toFixed(2)
    }
    totalPay = parseFloat(totalPay).toFixed(2)
    $('#id_non_continuing-biweekly_salary').val(biweeklySalary)
    $('.biweekly_rate_info').text(biweeklySalary)
    $('.biweekly_rate_calc').text('Total Pay (' + totalPay + ') / Pay Periods (' + payPeriods + ')')
    $('#id_non_continuing-vacation_hours').val(vacationHours)
    $('.vacation_hours_info').text(vacationHours)
    $('.vacation_hours_calc').text('Pay Periods (' + payPeriods + ') x (Weeks Vacation (' + weeksVacation + ') / 52.14) x Bi-Weekly Hours (' + biweeklyHours + ')')
    $('#id_non_continuing-gross_hourly').val(hourlyRate)
    $('.hourly_rate_info').text(hourlyRate)
    $('.hourly_rate_calc').text('Bi-Weekly Rate (' + biweeklySalary + ') / Bi-Weekly Hours (' + biweeklyHours + ')')
    $('#id_non_continuing-total_pay').val(totalPay)
    $('.total_pay_info').text(totalPay)
    $('.total_pay_calc').text('Total Gross (' + totalPay + ')')
}

function ncH () {
    biweeklyHours = $('#id_non_continuing-biweekly_hours').val()
    hourlyRate = $('#id_non_continuing-gross_hourly').val()
    vacationPay = $('#id_non_continuing-vacation_pay').val()
    payPeriods = $('#id_non_continuing-pay_periods').val()
    totalPay = (payPeriods * biweeklyHours * hourlyRate) * (1 + (vacationPay/100))
    totalPay = totalPay.toFixed(2)
    $('#id_non_continuing-total_pay').val(totalPay)
    $('.total_pay_info').text(totalPay)
    $('.total_pay_calc').text('Pay Periods (' + payPeriods + ') x Bi-Weekly Hours (' + biweeklyHours + ') x Hourly Rate (' + hourlyRate + ') x (1 + (Vacation Pay (' + vacationPay + ')/100))')
}

// for any hiring category, if it is backdated, show relevant fields for backdating an appointment
function backDatedPaymentMethod () {
    nc_backdated = $('#id_non_continuing-backdated').val()
    ra_backdated = $('#id_research_assistant-backdated').val()
    gras_backdated = $('#id_graduate_research_assistant-backdated').val()

    if (ra_backdated === 'True') {
        hide(rabw_fields)
        hide(rah_fields)
        hide(['research_assistant-ra_payment_method'])
        $('.biweekly_info').hide()
        show(ra_backdated_fields)
        raBackDated()
    } else if (nc_backdated === 'True') {
        hide(ncbw_fields)
        hide(nch_fields)
        hide(['non_continuing-nc_payment_method'])
        $('.biweekly_info').hide()
        show(nc_backdated_fields)
        ncBackDated()
    } else if (gras_backdated === 'True') {
        hide(grasbw_fields)
        hide(grasls_fields)
        hide(['graduate_research_assistant-gras_payment_method'])
        $('.biweekly_info').hide()
        show(gras_backdated_fields)
        grasBackDated()
    } else {
        hide(gras_backdated_fields)
        hide(ra_backdated_fields)
        hide(nc_backdated_fields)
    }
}

function raBackDated(){
    totalPay = $('#id_research_assistant-backdate_lump_sum').val()
    $('#id_research_assistant-total_pay').val(totalPay)
    $('.total_pay_info').text(totalPay)
    $('.total_pay_calc').text('Total Gross (' + totalPay + ')')

}

function grasBackDated(){
    totalPay = $('#id_graduate_research_assistant-backdate_lump_sum').val()
    $('#id_graduate_research_assistant-total_pay').val(totalPay)
    $('.total_pay_info').text(totalPay)
    $('.total_pay_calc').text('Total Gross (' + totalPay + ')')
}

function ncBackDated(){
    totalPay = $('#id_non_continuing-backdate_lump_sum').val()
    $('#id_non_continuing-total_pay').val(totalPay)
    $('.total_pay_info').text(totalPay)
    $('.total_pay_calc').text('Total Gross (' + totalPay + ')')
}

$(document).ready(function() {
    // prevent 'enter' key from submitting the form
    $(window).keydown(function(event){
        if(event.keyCode == 13) {
          event.preventDefault();
          return false;
        }
      });

    // prevent resubmission if user clicks back into the form, will just direct to first page
    // https://stackoverflow.com/questions/6833914/how-to-prevent-the-confirm-form-resubmission-dialog
    if ( window.history.replaceState ) {
    window.history.replaceState( null, null, window.location.href );
    }
    
    $('#id_intro-person').each(function() {
      $(this).autocomplete({
        source: '/data/students',
        minLength: 2,
        select: function(event, ui){
          $(this).data('val', ui.item.value)
        }
      })
    })  
    $('#id_intro-supervisor').each(function() {
        $(this).autocomplete({
          source: '/data/students',
          minLength: 2,
          select: function(event, ui){
            $(this).data('val', ui.item.value)
          }
        })
    }) 

    // don't let the user leave the page without scaring them
    window.onbeforeunload = function() {
        return "Your information will not be saved if you refresh/leave the form.";
    }  
    
    // unless it's save, submit or previous
    $('#save').click(function(){
        window.onbeforeunload = null;
    });

    $('#prev').click(function(){
        window.onbeforeunload = null;
    });

    $('#done').click(function(){
        window.onbeforeunload = null;
    });

    $('#done_draft').click(function(){
        window.onbeforeunload = null;
    });

    idFieldsUpdate()
    studentFieldsUpdate()
    hiringCategoryRec()

    fs2ChoiceUpdate()
    fs3ChoiceUpdate()

    // Start and end dates

    updatePayPeriods()
    updateBackDatedInfo()

    $('#id_dates-start_date').change(updatePayPeriods)
    $('#id_dates-end_date').change(updatePayPeriods)
    $('#id_dates-start_date').change(updateBackDated)
    $('#id_dates-start_date').change(updateBackDatedInfo)
    $('#id_dates-end_date').change(updateBackDated)
    $('#id_dates-end_date').change(updateBackDatedInfo)
    
    $('#id_dates-start_date').datepicker({'dateFormat': 'yy-mm-dd'})
    $('#id_dates-end_date').datepicker({'dateFormat': 'yy-mm-dd'})
    $('#id_funding_sources-fs1_start_date').datepicker({'dateFormat': 'yy-mm-dd'})
    $('#id_funding_sources-fs1_end_date').datepicker({'dateFormat': 'yy-mm-dd'})
    $('#id_funding_sources-fs2_start_date').datepicker({'dateFormat': 'yy-mm-dd'})
    $('#id_funding_sources-fs2_end_date').datepicker({'dateFormat': 'yy-mm-dd'})
    $('#id_funding_sources-fs3_start_date').datepicker({'dateFormat': 'yy-mm-dd'})
    $('#id_funding_sources-fs3_end_date').datepicker({'dateFormat': 'yy-mm-dd'})

    grasPaymentMethod()
    ncPaymentMethod()
    raPaymentMethod()
    backDatedPaymentMethod()

    // select if appointee does not have an ID
    $('#id_intro-nonstudent').change(idFieldsUpdate)
    
    // is the appointee a student?
    $('#id_intro-student').change(studentFieldsUpdate)
    $('#id_intro-usra').change(studentFieldsUpdate)
    $('#id_intro-research').change(studentFieldsUpdate)

    $('#id_intro-student').change(hiringCategoryRec)
    $('#id_intro-usra').change(hiringCategoryRec)
    $('#id_intro-research').change(hiringCategoryRec)
    $('#id_intro-thesis').change(hiringCategoryRec)

    // funding information
    $('#id_funding_sources-fs2_option').change(fs2ChoiceUpdate)
    $('#id_funding_sources-fs3_option').change(fs3ChoiceUpdate)

    // ra payment method
    $('#id_research_assistant-ra_payment_method').change(raPaymentMethod)
    $('#id_research_assistant-total_gross').change(raPaymentMethod)
    $('#id_research_assistant-biweekly_hours').change(raPaymentMethod)
    $('#id_research_assistant-weeks_vacation').change(raPaymentMethod)
    $('#id_research_assistant-gross_hourly').change(raPaymentMethod)
    $('#id_research_assistant-vacation_pay').change(raPaymentMethod)

    // nc payment method
    $('#id_non_continuing-nc_payment_method').change(ncPaymentMethod)
    $('#id_non_continuing-total_gross').change(ncPaymentMethod)
    $('#id_non_continuing-biweekly_hours').change(ncPaymentMethod)
    $('#id_non_continuing-weeks_vacation').change(ncPaymentMethod)
    $('#id_non_continuing-gross_hourly').change(ncPaymentMethod)
    $('#id_non_continuing-vacation_pay').change(ncPaymentMethod)

    // gras payment method
    $('#id_graduate_research_assistant-gras_payment_method').change(grasPaymentMethod)
    $('#id_graduate_research_assistant-total_gross').change(grasPaymentMethod)

    // backdated appointments
    $('#id_non_continuing-backdate_lump_sum').change(ncBackDated)
    $('#id_research_assistant-backdate_lump_sum').change(raBackDated)
    $('#id_graduate_research_assistant-backdate_lump_sum').change(grasBackDated)
})