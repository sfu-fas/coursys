function guess_pay_periods() {
    date_1 = $('#id_pay_start').val();
    date_2 = $('#id_pay_end').val();
    moment_1 = moment(date_1, 'YYYY-MM-DD');
    moment_2 = moment(date_2, 'YYYY-MM-DD');
    days = Math.abs(moment_2.diff(moment_1, 'days'))+1;
    payperiods = Math.round(days/14);
    $('#id_payperiods').val(payperiods);
    $('#id_payperiods').effect('highlight');
}

function get_grad_status(emplid) {
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
    let person_id = $('#id_person');
    person_id.change(function() {
        if ($(this).val().length === 9)
        {
            get_grad_status($(this).val());
        }
    });
    person_id.change();
    $('#id_payperiods').each(function(){ // if there's an id_payperiods, activate code to guess the value
        $('#id_pay_start').change(guess_pay_periods);
        $('#id_pay_end').change(guess_pay_periods);
    });
});