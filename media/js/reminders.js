var reminder_type_fields = ['role_unit', 'course'];
var date_type_fields = ['month', 'day', 'week', 'weekday'];

function hide_input(field) {
    $('label[for=id_' + field + ']').parent().hide();
    $('#id_' + field).parent().parent().hide();
}
function show_input(field) {
    $('label[for=id_' + field + ']').parent().show();
    $('#id_' + field).parent().parent().show();
}

function reminder_type_update() {
    var value = $('.reminder-form input[type=radio][name=reminder_type]:checked').val();
    for ( f of reminder_type_fields ) {
        hide_input(f);
    }

    if ( value == 'PERS' ) {
    } else if ( value == 'INST' ) {
        show_input('course');
    } else if ( value == 'ROLE' ) {
        show_input('role_unit');
    }
}

function date_type_update() {
    var value = $('.reminder-form input[type=radio][name=date_type]:checked').val();
    for ( f of date_type_fields ) {
        hide_input(f);
    }

    if ( value == 'YEAR' ) {
        show_input('month');
        show_input('day');
    } else if ( value == 'SEM' ) {
        show_input('week');
        show_input('weekday');
    }
}

$(document).ready(function(){
    $('.reminder-form input[type=radio][name=reminder_type]').change(reminder_type_update);
    reminder_type_update();
    $('.reminder-form input[type=radio][name=date_type]').change(date_type_update);
    date_type_update();
});