function add(){
	var total_forms = $('#id_form-TOTAL_FORMS').val()*1;
	var max_forms = $('#id_form-MAX_NUM_FORMS').val()*1;
	if (total_forms < max_forms){
		newForm = $('#supervisor-form-0').clone(true);
		
		new_id=$(newForm).attr('id').replace('-0', '-' + total_forms);
		$(newForm).attr('id', new_id);
		
		formset_label = newForm.find('p[id$="label"]')
		formset_label.html('Supervisor ' + (total_forms+1) + ':');
		new_id=formset_label.attr('id').replace('-0', '-' + total_forms);
		formset_label.attr('id',new_id);
		
		newForm.find(':input').each(function() {
	        var new_name = $(this).attr('name').replace('-0-','-' + total_forms + '-');
	        var new_id = 'id_' + new_name;
       		$(this).attr({'name': new_name, 'id': new_id});	
        	$(this).val('');
        	if(new_name.indexOf("id")!=-1){
        		$(this).val(''); // ensures id gets cleared
        	}
	        if(new_id.indexOf("position")!=-1){
        		$(this).val((total_forms+1)); //increment position
	        }
	    });
	    	    
	    newForm.find('label').each(function() {
	        var new_for = $(this).attr('for').replace('-0-','-' + total_forms + '-');
	        $(this).attr('for', new_for);
	    });
	    
		$('#id_form-TOTAL_FORMS').val(total_forms+1);
		$('#supervisor-forms').append($(newForm));
		if (total_forms+1 == max_forms){
			$('#add_btn').attr('disabled', true).css('background-color','#bba');
		}
	}
}



function update(el, url) {
	$.ajax({
		url : url,
		success : function(data) {
			if(console && console.log) {
				console.log(data);
			}
		}
	});
}