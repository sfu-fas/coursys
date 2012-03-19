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
        $('#label_person_name').text(" " + label);
        update_person($(this).data("val"));
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

function update_person(id) {
  $.getJSON("/data/scholarships/" + id, function(json) {
    var options = '<option value="" >---------</option>';
    for (var i=0; i < json.length; i++) {
      options += '<option value="' + json[i].value +'">' + json[i].display + '</option>';
    }
    $('#id_scholarship').html(options);
  });
}

$(document).ready(function() {
  name_label = document.createElement("span");
  name_label.id = "label_person_name";
  /*
  $.getJSON("/data/scholarships/200000193", function(json) {
    alert(json[1].display);
  });
  */
  $('#id_person').parent().append(name_label);
  $("id_person").focus();
  ra_autocomplete('id_person');
  $("#id_start_date").datepicker({'dateFormat': 'yy-mm-dd'});
  $("#id_end_date").datepicker({'dateFormat': 'yy-mm-dd'});
  $("#id_lump_sum_pay").change(function() {
    update_lump_sum();
  });
  $("#id_biweekly_pay").change(function() {
    update_biweekly();
  });
  $("#id_pay_periods").change(function() {
    update_lump_sum();
  });
  $("#id_hourly_pay").change(function() {
    update_hourly();
  });
  $("#id_hours").change(function() {
    update_lump_sum();
  });
  $("#id_person").change(function() {
    update_person();
  });
});