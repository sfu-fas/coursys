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

function update_pay_frequency() {
	var v = $("#id_pay_frequency").val();
	if ( v == 'L' ) {
		$("#id_hourly_pay").prop('disabled', true);
		$("#id_biweekly_pay").prop('disabled', true);
		$("#id_hours").prop('disabled', true).val(1);
		$("#id_pay_periods").prop('disabled', true).val(1);
		update_lump_sum();
	} else {
		$("#id_hourly_pay").prop('disabled', false);
		$("#id_biweekly_pay").prop('disabled', false);
		$("#id_hours").prop('disabled', false);
		$("#id_pay_periods").prop('disabled', false);
	}
}

function update_pay_periods() {
	var start_text = $("#id_start_date").val();
	var end_text = $("#id_end_date").val();
	var url = payperiods_url + "?start=" + start_text + "&end=" + end_text;
	$.ajax({
		url: url,
		success: function(data) {
			$("#id_pay_periods").val(data);
		},
	});
}


function update_person(id) {
    $.getJSON("/data/scholarships/" + id, function(json) {
    var options = '<option value="">—</option>';
    for (var i=0; i < json.length; i++) {
      options += '<option value="' + json[i].value +'">' + json[i].display + '</option>';
    }
    $('#id_scholarship').html(options);
  });
}

function get_person_info(emplid) {
	$('dl.dlform').first().before('<div id="programs">...</div>');	
	$.ajax({
		url: personinfo_url + '?emplid=' + emplid,
		success: function(data, textStatus, jqXHR) {
			if (data['programs']) {
				var html = '';
				html += '<h3>Program(s)</h3><ul>';
				$(data['programs']).each(function(e,prog) {
					html += '<li>';
					html += prog['program'] + ', ' + prog['unit'] + ' (' + prog['status'] + ')';
					html += '</li>';
				});
				html += '</ul>';
				$('div#programs').html(html);
	        }
		},
	})
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
  $("#id_lump_sum_pay").change(update_lump_sum);
  $("#id_biweekly_pay").change(update_biweekly);
  $("#id_pay_periods").change(update_lump_sum);
  $("#id_hourly_pay").change(update_hourly);
  $("#id_hours").change(update_lump_sum);
  $("#id_pay_frequency").change(update_pay_frequency);
  update_pay_frequency();
  $("#id_person").change(update_person);
  $("#id_start_date").change(update_pay_periods);
  $("#id_end_date").change(update_pay_periods);
  update_pay_periods();
  if ( emplid ) {
  	get_person_info(emplid);
  }
});