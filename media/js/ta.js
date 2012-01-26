var WEEKS_PER_SEMESTER = 13

$(function(){
	$('#id_base_units').change(function(){
		if($(this).val()<=0){
			alert("Base units cannot be negative!");
		}
		$('#maxHours').html($(this).val()*42);
		
	});
	$('#maxHours').html($('#id_base_units').val()*42);
	
	$("input[id$='_0']").change(function(){
		duty = extractDutyNameFromElement(this);
		updateTotal(duty);
		updateTotalHours();
	});
	
	$("input[id$='_1']").change(function(){
		updateTotalHours();
	})
	
}());

function extractDutyNameFromElement(element){
	ele_id = $(element).attr('id');
	duty = ele_id.substring(0,ele_id.length-2);
	return duty;
}

function updateAllTotals(){
	$("input[id$='_0']").each(function(){
			duty = extractDutyNameFromElement(this);
			updateTotal(duty);
	})
}

function updateTotal(duty){
	$('#'+duty+'_1').val(($('#'+duty+'_0').val()*WEEKS_PER_SEMESTER));
}

function updateTotalHours(){
	total = 0;
	$("input[id$='_1']").each(function(){
		total += $(this).val()*1; // *1 to cast from string to a number
	});
	$('#totalHours').html(total);
}
