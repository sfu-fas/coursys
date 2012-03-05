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
/*
function update_hourly() {
    var rate = $("#id_rate").val();
    var amount = $("#id_amount").val();
    var hours_input = $("#id_hours").val();
    if (amount !== "") {
        if (rate == "H") {
            $('#id_hourly_rate').text("Hourly Rate: $" + amount);
        }
        else if ((rate == "L" || rate == "B") && hours_input !== "") {
            var total = parseFloat(amount, 10);
            var num_hours = parseFloat(hours_input, 10);
            var num_minutes = parseFloat($("#id_minutes").val());
            if (isNaN(num_minutes)){
                num_minutes = 0;
            }
            var pay_rate = (total / (num_hours + (num_minutes / 60)));
            $('#id_hourly_rate').text("Hourly Rate: $" + pay_rate.toFixed(2));
        }
    }
}

$(document).ready(function() {
    $('#id_periods').parent().append('<div id="id_hourly_rate"></div>');
    $("#id_amount").change(function() {
        update_hourly();
    });
    $("#id_rate").change(function() {
        update_hourly();
    });
    $("#id_hours").change(function() {
        update_hourly();
    });
    $("#id_minutes").change(function() {
        update_hourly();
    });
    $("#id_periods").change(function() {
        update_hourly();
    });
});​
*/