var WEEKS_PER_SEMESTER = 13

$(function(){
	getErrorList = function(el){
		erl = el.siblings(".errorlist");
		if(erl.length > 0){
			return erl;
		}
		else {
			el.before("<ul class=\"errorlist\"></ul>");
			return el.prev();
		}
	}
	
	$('#id_base_units').change(function() {
		el = getErrorList($(this).parent());
		// see ta.forms.TUGForm.base_units for appropriate error messages
		// there's probably a nice django plugin/something that does this automatically
		//   look at that if this needs to be maintained a lot

		emptymsg = el.children("li:contains('Base units are required.')");
		nanmsg = el.children("li:contains('Base units must be a number.')");
		posmsg = el.children("li:contains('Base units must be positive.')");
		if($.trim($(this).val()).length == 0) {
			if(emptymsg.length == 0) {
				el.append("<li>Base units are required.</li>");
			}
			nanmsg.remove();
			posmsg.remove();
			return;
		}
		else {
			emptymsg.remove();
		}
		if(isNaN($(this).val())) {
			if(nanmsg.length == 0) {
				el.append("<li>Base units must be a number.</li>");
			}
		}
		else {
			nanmsg.remove();
		}
		if($(this).val()<=0) {
			//alert("Base units cannot be negative!");
			if(posmsg.length == 0) {
				el.append("<li>Base units must be positive.</li>");
			}
		}
		else {
			posmsg.remove();
			// also set the holiday hours if it's unset
			
		}
		if(!(isNaN($(this).val()) || $(this).val()<=0)) {
			if (!($("#id_holiday-total").val())) {
	            $("#id_holiday-total").val($(this).val());
			}
		}
		if(el.children().length == 0) {
			el.remove();
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
	
//	$("#id_base_units").change(function(){
//        if (!($("#id_holiday-total").val())) {
//            $("#id_holiday-total").val($(this).val());
//    }
//	})
	
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
