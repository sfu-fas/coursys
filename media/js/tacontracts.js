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

$(document).ready(function(){
    $('#id_payperiods').each(function(){ // if there's an id_payperiods, activate code to guess the value
        $('#id_pay_start').change(guess_pay_periods);
        $('#id_pay_end').change(guess_pay_periods);
    });
});