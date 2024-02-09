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

function getGuessPayPeriods () {
    var payPeriods = guessPayPeriods($('#id_pay_start').val(), $('#id_pay_end').val())
    $('#id_payperiods').val(payPeriods)
    $('#id_payperiods').effect('highlight');
}

function getGradStatus(emplid) {
    $.ajax({
        type: 'GET',
        url: persongradprograms_url + '?emplid=' + emplid,
        success: function(data) {
            var html = '';
            html += '<div class="info-bubble"><h3>Current Grad Status <i class="fa fa-info-circle"></i></h3>';
            html += '<span class="info">Displays any graduate programs that this person has a valid status for during ' + data['semester'] + '.</span></div><ul>';
            if (data['grad_program'].length == 0) {
                html += '<li><i>No valid grad programs found for this person.</i></li>';
            } else {
                $(data['grad_program']).each(function(e, grad_program) {
                    html += '<p><li><a href="/grad/' + grad_program['slug'] + '"><i class="fa fa-mortar-board"></i> ' + grad_program['name'] + '</a><br>'
                    html += grad_program['unit'] + '<br>'
                    if (grad_program['active_status']) {
                        html += ' <div id="grad_active"><b>(' + grad_program['status'] + ')</b></div>'
                    } else {
                        html += ' <div id="grad_warning"><b>(' + grad_program['status'] + ')</b></div>'
                    }
                    html += '</li></p>';
                });
            }
            html += '</ul>';
            $('div#grad_status').html(html);
        },
        error: function(xhr) {
            $('div#grad_status').html("Error retrieving this person's grad programs (ID may not be in the system).");
        }
    });
}

$(document).ready(function(){
    $('dl.dlform').first().before('<div id="grad_status"></div>');
    let personId = $('#id_person');
    personId.change(function() {
        if ($(this).val().length === 9)
        {
            getGradStatus($(this).val());
        }
    });
    personId.change();
    $('#id_payperiods').each(function(){ // if there's an id_payperiods, activate code to guess the value
        $('#id_pay_start').change(getGuessPayPeriods);
        $('#id_pay_end').change(getGuessPayPeriods);
    });
});