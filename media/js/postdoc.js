function hideInput(field) {
    $('label[for=id_' + field + '_0]').parent().hide();
    $('label[for=id_' + field + ']').parent().hide();
    $('#id_' + field).parent().parent().hide();
}

function showInput(field) {
    $('label[for=id_' + field + '_0]').parent().show();
    $('label[for=id_' + field + ']').parent().show();
    $('#id_' + field).parent().parent().show();
}

function updateRelocationReimbursement() {
    if ($('input[name="relocation_reimbursement"]:checked').val() === 'True') {
        showInput('relocation_reimbursement_amount');
    } else {
        hideInput('relocation_reimbursement_amount');
    }
}

function updateLumpSumPayment() {
    var lumpSumChoice = $('input[name="has_lump_sum_payment"]:checked').val();

    if (lumpSumChoice === 'True') {
        hideInput('annual_salary_amount');
        $('#id_annual_salary_amount').val('0');
        showInput('lump_sum_payment');
    } else if (lumpSumChoice === 'False') {
        showInput('annual_salary_amount');
        hideInput('lump_sum_payment');
        $('#id_lump_sum_payment').val('0');
    } else {
        hideInput('annual_salary_amount');
        hideInput('lump_sum_payment');
    }
}

function updateWorkHours() {
    if ($('#id_work_hours').val() === 'PART_TIME') {
        showInput('hours_of_work');
    } else {
        hideInput('hours_of_work');
        $('#id_hours_of_work').val('35');
    }
}

function updateVisaLink() {
    var link = $('#postdoc-visa-link');
    if (!link.length) {
        return;
    }

    var status = $('#id_work_eligibility_status').val();
    if (!(status === 'PERMANENT_RESIDENT' || status === 'INTERNATIONAL')){
        link.hide();
        return;
    }

    var baseUrl = '/visas/new_visa';
    link.attr('href', baseUrl);
    link.html('<b>+ Add New Visa</b>');
    link.show();
}

$(document).ready(function() {
    $('#id_person').autocomplete({
        source: '/data/students',
        minLength: 2,
        select: function(event, ui) {
            $(this).data('val', ui.item.value);
        }
    });
    $('input[id$="-supervisor"]').autocomplete({
        source: '/data/students',
        minLength: 2,
        select: function(event, ui) {
            $(this).data('val', ui.item.value);
        }
    });

    updateRelocationReimbursement();
    updateLumpSumPayment();
    updateWorkHours();
    updateVisaLink();

    $('#id_relocation_reimbursement').change(updateRelocationReimbursement);
    $('#id_has_lump_sum_payment').change(updateLumpSumPayment);
    $('#id_work_hours').change(updateWorkHours);
    $('#id_work_eligibility_status').change(updateVisaLink);
    $('#id_doctorate_completed_date').datepicker({'dateFormat': 'yy-mm-dd'});
    $('#id_start_date').datepicker({'dateFormat': 'yy-mm-dd'});
    $('#id_end_date').datepicker({'dateFormat': 'yy-mm-dd'});
    $('input[id$="-start_date"]').datepicker({'dateFormat': 'yy-mm-dd'});
    $('input[id$="-end_date"]').datepicker({'dateFormat': 'yy-mm-dd'});

});
