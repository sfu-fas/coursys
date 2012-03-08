function ra_autocomplete() {
    var regexp = /(,.*)/;
    var label;
    $('#id_person').each(function() {
        $(this).autocomplete({
            source:'/data/students',
            minLength: 2,
            select: function(event, ui){
                $(this).data("val", ui.item.value);
                label = ui.item.label.replace(regexp, "")
                $('#id_person').parent().append(document.createTextNode(" " + label));
            }
        }).bind('blur', function(){
            $(this).val($(this).data("val"))
        });
    });
}
function update_lump_sum() {
    var lump_sum = parseFloat($("#id_lump_sum_pay").val());
    var num_periods = parseFloat($("#id_pay_periods").val());
    var num_hours = parseFloat($("#id_hours").val());
    $("#id_hourly_pay").val((lump_sum / (num_periods * num_hours)).toFixed(2));
    $("#id_biweekly_pay").val((lump_sum / num_periods).toFixed(2));  
}

function update_biweekly() {
    var biweekly = parseFloat($("#id_biweekly_pay").val());
    var num_periods = parseFloat($("#id_pay_periods").val());
    var num_hours = parseFloat($("#id_hours").val());
    $("#id_lump_sum_pay").val((biweekly * num_periods).toFixed(2));
    $("#id_hourly_pay").val((biweekly / num_hours).toFixed(2));
}

function update_hourly() {
    var hourly = parseFloat($("#id_hourly_pay").val());
    var num_periods = parseFloat($("#id_pay_periods").val());
    var num_hours = parseFloat($("#id_hours").val());
    $("#id_lump_sum_pay").val((hourly * num_hours * num_periods).toFixed(2));
    $("#id_biweekly_pay").val((hourly * num_hours).toFixed(2));
}