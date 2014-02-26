function add_course(){
	var total_forms = $("#id_form-TOTAL_FORMS").val()*1;
	var max_forms = $("#id_form-MAX_NUM_FORMS").val()*1;
	if (total_forms < max_forms){
		newForm = $("#course-form-0").clone(true);
		new_id=$(newForm).attr("id").replace("-0", "-" + total_forms);
		$(newForm).attr("id", new_id);
		
		formset_label = newForm.find('h3')
		formset_label.html('Course ' + (total_forms+1) + ":");

		newForm.find(':input').each(function() {
	        var new_name = $(this).attr('name').replace('-0' + '-','-' + total_forms + '-');
	        var new_id = 'id_' + new_name;
	        $(this).attr({'name': new_name, 'id': new_id}).val('');
	    });
	    newForm.find('label').each(function() {
	        var new_for = $(this).attr('for').replace('-0' + '-','-' + total_forms + '-');
	        $(this).attr('for', new_for);
	    });
	    
		$("#id_form-TOTAL_FORMS").val(total_forms+1);
		$("#course-forms").append($(newForm).html());
		if (total_forms+1 == max_forms){
			$("#add_btn").attr("disabled", true).css("background-color","#bba");
		}
	}
	
}

function update(url) {
	$.ajax({
		url : url,
		success : function(data) {
			if(console && console.log) {
				console.log(data);
			}
		}
	});
}
