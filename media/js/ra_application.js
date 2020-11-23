var noIdFields = ['first_name', 'last_name', 'email_address']
var idFields = ['person']

var studentFields = ['coop', 'mitacs']
var studentNonMitacsFields = ['thesis']
var studentOnlyFields = ['coop', 'mitacs', 'thesis']

var raPaymentHourlyFields = ['gross_hourly', 'vacation_pay']
var raPaymentBiWeeklyFields = ['total_gross', 'days_vacation']
var raPaymentFields = ['total_gross', 'gross_hourly', 'days_vacation', 'vacation_pay']
var raOnlyFields = ['ra_benefits', 'ra_payment_method', 'ra_duties_ex', 'ra_duties_dc', 'ra_duties_pd', 'ra_duties_im', 'ra_duties_eq', 
'ra_duties_su', 'ra_duties_wr', 'ra_duties_pm', 'ra_other_duties']

var grasPaymentLumpSumFields = ['total_gross', 'days_vacation']
var grasPaymentBiWeeklyFields = ['biweekly_pay', 'days_vacation']
var grasPaymentFields = ['biweekly_pay', 'total_gross', 'lump_sum', 'days_vacation']
var grasOnlyFields = ['gras_payment_method']

var fs2Fields = ['fs2_unit', 'fs2_fund', 'fs2_project']

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
function set (fields, val) {
    for (let i = 0; i < fields.length; i++) {
        var checked = $('input[name=' + fields[i] + ']:checked')
        checked.val([val])
    }
}

function setZero (fields) {
    for(let i = 0; i < fields.length; i++) {
        $('#id_'+ + fields[i]).val(0)
    }
}

// guessing pay periods for their info
function guessPayPeriods () {
    date_1 = new Date ($('#id_start_date').val())
    date_2 = new Date ($('#id_end_date').val())
    
    diff = (Math.abs(date_2 - date_1))/(86400000 * 14)
    payPeriods = diff.toFixed(1)
    return payPeriods
}

// field change for applicants with ids vs no ids
function idFieldsUpdate () {
    if ($('#id_nonstudent').is(':checked')) {
        show(noIdFields)
        hide(idFields)
    } else {
        hide(noIdFields)
        show(idFields)
    }
}

function studentFieldsUpdate () {
    var student_checked = $('input[name=student]').is(':checked')
    var student = $('input[name=student]:checked')
    if (student.val() != 'N' && student_checked === true) {
        show(studentFields)
    } else {
        hide(studentOnlyFields)
        set(studentOnlyFields, 'None')
    }
}

function mitacsFieldsUpdate () {
    var mitacs = $('input[name=mitacs]:checked')
    if (mitacs.val() === 'False') {
        show(studentNonMitacsFields)
    } else {
        hide(studentNonMitacsFields)
        set(studentNonMitacsFields, 'None')
    }
}

function researchAssistant () {
    $('#id_hiring_category').val('RA')

    $('.need_more_info').hide()
    $('.ra_info').show()
    $('.gras_info').hide()
    $('.ra_section').show()

    // Payment Method
    hide(grasOnlyFields)
    set(grasOnlyFields, 'None')
    hide(grasPaymentFields)
    setZero(grasPaymentFields)
    
    // RA Only Options
    show(raOnlyFields)
}

function graduateResearchAssistant () {
    $('#id_hiring_category').val('GRAS')

    $('.need_more_info').hide()
    $('.gras_info').show()
    $('.ra_info').hide()
    $('.ra_section').hide()

    hide(raPaymentFields)
    setZero(raPaymentFields)
    hide(raOnlyFields)
    set(raOnlyFields, 'None')

    show(grasOnlyFields)
}

function raPaymentMethod() {
    var raPaymentMethod = $('input[name=ra_payment_method]:checked')
    
    if (raPaymentMethod.val() === 'H') {
        hide(raPaymentBiWeeklyFields)
        setZero(raPaymentBiWeeklyFields)
        show(raPaymentHourlyFields)
    } else if (raPaymentMethod.val() === 'BW') {
        hide(raPaymentHourlyFields)
        setZero(raPaymentHourlyFields)
        show(raPaymentBiWeeklyFields)
    } else {
        hide(raPaymentFields)
        setZero(raPaymentFields)
        grasPaymentMethod()
    }
    calculateTotalPay()
}

function grasPaymentMethod () {
    var grasPaymentMethod = $('input[name=gras_payment_method]:checked')
    if (grasPaymentMethod.val() === 'LE' || grasPaymentMethod.val() === 'LS') {
        hide(grasPaymentBiWeeklyFields)
        setZero(grasPaymentBiWeeklyFields)
        show(grasPaymentLumpSumFields)
    } else if (grasPaymentMethod.val() === 'BW') {
        hide(grasPaymentLumpSumFields)
        setZero(grasPaymentLumpSumFields)
        show(grasPaymentBiWeeklyFields)
    } else {
        hide(grasPaymentFields)
        setZero(grasPaymentFields)
    }
    calculateTotalPay()
}

function hiringCategoryRec () {
    var student = $('input[name=student]:checked')
    var thesis = $('input[name=thesis]:checked')
    var mitacs =  $('input[name=mitacs]:checked')
    
    if (student.val() === 'N') {   
        researchAssistant()
    } else if (thesis.val() === 'True') {
        graduateResearchAssistant()
    } else if (mitacs.val() === 'True') {
        graduateResearchAssistant()
    } else if (mitacs.val() === 'False' & thesis.val() === 'False') {
        researchAssistant()
    } else {
        $('.need_more_info').show()
        $('.ra_info').hide()
        $('.gras_info').hide()
        hide(raOnlyFields)
        set(raOnlyFields, 'None')
        hide(grasOnlyFields)
        set(grasOnlyFields, 'None')
        hide(grasPaymentFields)
        setZero(grasPaymentFields)
        hide(raPaymentFields)
        setZero(raPaymentFields)
        $('.ra_section').hide()
    }
}

function fsChoiceUpdate () {
    if ($('#id_fs2_option').is(':checked')) {
        show(fs2Fields)
    } else {
        hide(fs2Fields)
    }
}

function calculateTotalPay () {
    var grasPaymentMethod = $('input[name=gras_payment_method]:checked')
    var raPaymentMethod = $('input[name=ra_payment_method]:checked')
    var payPeriods = guessPayPeriods()
    $('.pay_periods_info').text(payPeriods)
    if (grasPaymentMethod.val() === 'LE' || grasPaymentMethod.val() === 'LS') {
        totalPay = $('#id_total_gross').val()
        $('#id_total_pay').val(totalPay)
        $('.total_pay_info').text(totalPay)
    } else if (grasPaymentMethod.val() === 'BW') {
        biweeklyPay = $('#id_biweekly_pay').val()
        totalPay = biweeklyPay * payPeriods
        $('#id_total_pay').val(totalPay)
        $('.total_pay_info').text(totalPay)
    } else if (raPaymentMethod.val() === 'H') {
        grossHourly = $('#id_gross_hourly').val()
        biweeklyHours = $('#id_biweekly_hours').val()
        totalPay = grossHourly * biweeklyHours * payPeriods
        $('#id_total_pay').val(totalPay)
        $('.total_pay_info').text(totalPay)
    } else if (raPaymentMethod.val() === 'BW') {
        totalPay = $('#id_total_gross').val()
        $('#id_total_pay').val(totalPay)
        $('.total_pay_info').text(totalPay)
    } else {
        $('#id_total_pay').val(0)
        $('.total_pay_info').text('0.00')
    }
}

$(document).ready(function() {
    $('#id_person').each(function() {
      $(this).autocomplete({
        source: '/data/students',
        minLength: 2,
        select: function(event, ui){
          $(this).data('val', ui.item.value)
        }
      })
    })  
    $('#id_supervisor').each(function() {
        $(this).autocomplete({
          source: '/data/students',
          minLength: 2,
          select: function(event, ui){
            $(this).data('val', ui.item.value)
          }
        })
    }) 
    idFieldsUpdate()
    mitacsFieldsUpdate()
    studentFieldsUpdate()
    idFieldsUpdate()
    fsChoiceUpdate()
    hiringCategoryRec()
    raPaymentMethod()
    grasPaymentMethod()
    calculateTotalPay()

    // start and end dates
    $('#id_start_date').datepicker({'dateFormat': 'yy-mm-dd'})
    $('#id_end_date').datepicker({'dateFormat': 'yy-mm-dd'})

    // select if appointee does not have an ID
    $('#id_nonstudent').change(idFieldsUpdate)

    // is the appointee a student?
    $('#id_student').change(studentFieldsUpdate)
    $('#id_mitacs').change(mitacsFieldsUpdate)

    // funding information
    $('#id_fs2_option').change(fsChoiceUpdate)

    // hiring category changes
    $('#id_student').change(hiringCategoryRec)
    $('#id_mitacs').change(hiringCategoryRec)
    $('#id_thesis').change(hiringCategoryRec)

    // gras payment method
    $('#id_ra_payment_method').change(raPaymentMethod)
    $('#id_gras_payment_method').change(grasPaymentMethod)

    // if any of these change, we need to update total pay (which will also update pay periods)
    $('#id_biweekly_pay').change(calculateTotalPay)
    $('#id_days_vacation').change(calculateTotalPay)
    $('#id_gross_hourly').change(calculateTotalPay)
    $('#id_total_gross').change(calculateTotalPay)
    $('#id_vacation_pay').change(calculateTotalPay)
    $('#id_biweekly_hours').change(calculateTotalPay)
    $('#id_hiring_category').change(calculateTotalPay)
    $('#id_start_date').change(calculateTotalPay)
    $('#id_end_date').change(calculateTotalPay)

})
