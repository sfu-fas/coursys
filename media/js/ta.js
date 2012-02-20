var WEEKS_PER_SEMESTER = 13

$(function(){
	$('#id_base_units').change(function(){
		if($(this).val()<=0){
			alert("Base units cannot be negative!");
		}
		$('#maxHours').html($(this).val()*42);
		
	});
	$('#maxHours').html($('#id_base_units').val()*42);
	
	$("input[id$='-weekly']").change(function(){
		duty = extractDutyNameFromElement(this);
		updateTotal(duty);
		updateTotalHours();
	});
	
	$("input[id$='-total']").change(function(){
		updateTotalHours();
	})
	
	$("#id_base_units").change(function(){
        if (!($("#id_holiday-total").val())) {
            $("#id_holiday-total").val($(this).val());
    }
	})
	
}());

function extractDutyNameFromElement(element){
	ele_id = $(element).attr('id');
	duty = ele_id.substring(0,ele_id.length-"-weekly".length);
	return duty;
}

function updateAllTotals(){
	$("input[id$='-weekly']").each(function(){
			duty = extractDutyNameFromElement(this);
			updateTotal(duty);
	})
	$("#id_holiday-total").val($("#id_base_units").val())
}

function updateTotal(duty){
	$('#'+duty+'-total').val(($('#'+duty+'-weekly').val()*WEEKS_PER_SEMESTER));
}

function sum_jquery(node){
    total = 0;
	node.each(function(){
		total += $(this).val()*1; // *1 to cast from string to a number	
	});
    return total
}

function updateTotalHours(){
	$('#totalHours').html(sum_jquery($("input[id$='-total']")));
	$('#weeklyHours').html(sum_jquery($("input[id$='-weekly']")));
}
