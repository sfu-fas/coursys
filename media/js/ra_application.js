var noIdFields = ['first_name', 'last_name', 'email_address']
var idFields = ['person']

var studentFields = ['coop', 'mitacs']
var studentNonMitacsFields = ['thesis']
var studentOnlyFields = ['coop', 'mitacs', 'thesis']

var grasOptions = ['gras_payment_method']
var raOptions = ['ra_payment_method']

var raOnlyFields = ['ra_benefits', 'ra_payment_method', 'ra_duties_ex', 'ra_duties_dc', 'ra_duties_pd', 'ra_duties_im', 'ra_duties_eq', 
'ra_duties_su', 'ra_duties_wr', 'ra_duties_pm', 'ra_other_duties']

var fs2Fields = ['fs1_percentage', 'fs2_unit', 'fs2_fund', 'fs2_project', 'fs2_percentage', 'fs3_option']
var fs3Fields = ['fs3_unit', 'fs3_fund', 'fs3_project', 'fs3_percentage']

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
        setToNone(studentOnlyFields)
    }
}

function mitacsFieldsUpdate () {
    var mitacs = $('input[name=mitacs]:checked')
    if (mitacs.val() === 'False') {
        show(studentNonMitacsFields)
    } else {
        hide(studentNonMitacsFields)
        setToNone(studentNonMitacsFields)
    }
}

function researchAssistant () {
    $('#id_hiring_category').val('RA')

    $('.need_more_info').hide()
    $('.ra_info').show()
    $('.gras_info').hide()
    $('.ra_section').show()

    show(raOptions)

    hide(grasOptions)
    setToNone(grasOptions)

    $('.gras_biweekly_fields').hide()
    $('.gras_lump_sum_fields').hide()
}

function graduateResearchAssistant () {
    $('#id_hiring_category').val('GRAS')

    $('.need_more_info').hide()
    $('.gras_info').show()
    $('.ra_info').hide()
    $('.ra_section').hide()

    show(grasOptions)

    hide(raOptions)
    setToNone(raOptions)

    $('.ra_biweekly_fields').hide()
    $('.ra_hourly_fields').hide()
}

function raPaymentMethod() {
    var raPaymentMethod = $('input[name=ra_payment_method]:checked')

    if (raPaymentMethod.val() === 'H') {
        $('.biweekly_info').hide()
        $('.ra_biweekly_fields').hide()
        $('.ra_hourly_fields').show()
        raH()
    } else if (raPaymentMethod.val() === 'BW') {
        $('.biweekly_info').show()
        $('.ra_hourly_fields').hide()
        $('.ra_biweekly_fields').show()
        raBW()
    } else {
        $('.ra_biweekly_fields').hide()
        $('.ra_hourly_fields').hide()
        $('.biweekly_info').hide()
    }
}

function grasPaymentMethod () {
    var grasPaymentMethod = $('input[name=gras_payment_method]:checked')
    if (grasPaymentMethod.val() === 'LE' || grasPaymentMethod.val() === 'LS') {
        $('.biweekly_info').hide()
        $('.gras_biweekly_fields').hide()
        $('.gras_lump_sum_fields').show()
        grasLS()
    } else if (grasPaymentMethod.val() === 'BW') {
        $('.biweekly_info').show()
        $('.gras_biweekly_fields').show()
        $('.gras_lump_sum_fields').hide()
        grasBW()
    } else {
        $('.gras_biweekly_fields').hide()
        $('.gras_lump_sum_fields').hide()
        $('.biweekly_info').hide()
    }
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
        $('.ra_section').hide()
        $('.ra_biweekly_fields').hide()
        $('.ra_hourly_fields').hide()
        $('.gras_biweekly_fields').hide()
        $('.gras_lump_sum_fields').hide()

        hide(raOptions)
        hide(grasOptions)

        $('.biweekly_info').hide()

        $('#id_total_pay').val(0)
        $('.total_pay_info').text(0)

        $('.biweekly_rate_info').text(0)
        $('.hourly_rate_info').text(0)

        $('#id_grasbw_biweekly_salary').val(0)
        $('#id_grasbw_gross_hourly').val(0)

        $('#id_rabw_biweekly_salary').val(0)
        $('#id_rabw_gross_hourly').val(0)

        $('.ra_section').hide()
    }
}

function fs2ChoiceUpdate () {
    if ($('#id_fs2_option').is(':checked')) {
        show(fs2Fields)
    } else {
        hide(fs2Fields)
        hide(fs3Fields)
        $("#id_fs3_option").prop("checked", false);
    }
}

function fs3ChoiceUpdate() {
    if ($('#id_fs3_option').is(':checked')) {
        show(fs3Fields)
    } else {
        hide(fs3Fields)
    }
}

function grasLS () {
    totalPay = $('#id_grasls_total_gross').val()
    $('#id_total_pay').val(totalPay)
    $('.total_pay_info').text(totalPay)
}

function grasBW () {
    totalPay = $('#id_grasbw_total_gross').val()
    biweeklyHours = $('#id_grasbw_biweekly_hours').val()
    var payPeriods = guessPayPeriods()
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
    $('#id_grasbw_biweekly_salary').val(biweeklySalary)
    $('.biweekly_rate_info').text(biweeklySalary)
    $('#id_grasbw_gross_hourly').val(hourlyRate)
    $('.hourly_rate_info').text(hourlyRate)
    $('#id_total_pay').val(totalPay)
    $('.total_pay_info').text(totalPay)
}

function raBW () {
    totalPay = $('#id_rabw_total_gross').val()
    biweeklyHours = $('#id_rabw_biweekly_hours').val()
    var payPeriods = guessPayPeriods()
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
    $('#id_rabw_biweekly_salary').val(biweeklySalary)
    $('.biweekly_rate_info').text(biweeklySalary)
    $('#id_rabw_gross_hourly').val(hourlyRate)
    $('.hourly_rate_info').text(hourlyRate)
    $('#id_total_pay').val(totalPay)
    $('.total_pay_info').text(totalPay)
}

function raH () {
    biweeklyHours = $('#id_rah_biweekly_hours').val()
    hourlyRate = $('#id_rah_gross_hourly').val()
    vacationPay = $('#id_rah_vacation_pay').val()
    var payPeriods = guessPayPeriods()
    totalPay = (payPeriods * biweeklyHours * hourlyRate) * (1 + (vacationPay/100))
    $('#id_total_pay').val(totalPay)
    $('.total_pay_info').text(totalPay)
}

function updatePayPeriods () {
    var raPaymentMethod = $('input[name=ra_payment_method]:checked')
    var grasPaymentMethod = $('input[name=gras_payment_method]:checked')
    var payPeriods = guessPayPeriods()
    $('.pay_periods_info').text(payPeriods)

    if (raPaymentMethod.val() === 'H') {
        raH()
    } else if (raPaymentMethod.val() === 'BW') {
        raBW()
    } else if (grasPaymentMethod.val() === 'LE' || grasPaymentMethod.val() === 'LS') {
        grasLS()
    } else if (grasPaymentMethod.val() === 'BW') {
        grasBW()
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

    grasPaymentMethod()
    raPaymentMethod()

    fs2ChoiceUpdate()
    fs3ChoiceUpdate()

    hiringCategoryRec()

    updatePayPeriods()

    // Start and end dates
    $('#id_start_date').change(updatePayPeriods)
    $('#id_end_date').change(updatePayPeriods)
    
    // start and end dates
    $('#id_start_date').datepicker({'dateFormat': 'yy-mm-dd'})
    $('#id_end_date').datepicker({'dateFormat': 'yy-mm-dd'})

    // select if appointee does not have an ID
    $('#id_nonstudent').change(idFieldsUpdate)

    // is the appointee a student?
    $('#id_student').change(studentFieldsUpdate)
    $('#id_mitacs').change(mitacsFieldsUpdate)

    // funding information
    $('#id_fs2_option').change(fs2ChoiceUpdate)
    $('#id_fs3_option').change(fs3ChoiceUpdate)

    // hiring category changes
    $('#id_student').change(hiringCategoryRec)
    $('#id_mitacs').change(hiringCategoryRec)
    $('#id_thesis').change(hiringCategoryRec)

    // gras payment method
    $('#id_ra_payment_method').change(raPaymentMethod)
    $('#id_gras_payment_method').change(grasPaymentMethod)

    $('#id_rabw_total_gross').change(raBW)
    $('#id_rabw_biweekly_hours').change(raBW)

    $('#id_rah_gross_hourly').change(raH)
    $('#id_rah_vacation_pay').change(raH)
    $('#id_rah_biweekly_hours').change(raH)

    $('#id_grasls_total_gross').change(grasLS)
    
    $('#id_grasbw_total_gross').change(grasBW)
    $('#id_grasbw_biweekly_hours').change(grasBW)
})
