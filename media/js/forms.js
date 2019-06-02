
function hide_input(field) {
    $('label[for=id_' + field + ']').parent().hide();
    $('#id_' + field).parent().parent().hide();
}
function show_input(field) {
    $('label[for=id_' + field + ']').parent().show();
    $('#id_' + field).parent().parent().show();
}

function email_fields_update() {
    if ($('#id_autoconfirm').is(':checked')) {
        show_input('emailsubject');
        show_input('emailbody');
    }
    else {
        hide_input('emailsubject');
        hide_input('emailbody');
    }

}

$(document).ready(function(){
    $('#id_autoconfirm').change(email_fields_update);
    email_fields_update();
});