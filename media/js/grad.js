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
        	if(new_name.indexOf('id')!=-1){
        		$(this).val(''); // ensures id gets cleared
        	}
	        if(new_id.indexOf('position')!=-1){
        		$(this).val((total_forms+1)); //increment position
	        }
	        if(new_name.indexOf("supervisor_0")!=-1){
	        	$(this).find('option').removeAttr('selected');
	        	// copy event handlers. For some reason, clone(true) is not cloning the handlers as it should.
	        	$(this).change(function(){
	        		processSelections($('select[id*="supervisor"]'));
					// exclude potential
					if($(this).attr('id').indexOf('pot')==-1){
						$('#'+$(this).attr('id').replace('supervisor_0','external')).val('');
					}
	        	})
	        }
	    });
	    	    
	    newForm.find('label').each(function() {
	        var new_for = $(this).attr('for').replace('-0-','-' + total_forms + '-');
	        $(this).attr('for', new_for);
	    });
	    
		$('#id_form-TOTAL_FORMS').val(total_forms+1);
		$('#supervisor-forms').append($(newForm));
		processSelections($('select[id*="supervisor"]'));
		if (total_forms+1 == max_forms){
			$('#add_btn').attr('disabled', true).css('background-color','#bba');
		}
	}
}

var currentSelections = new Object();

function processSelections(selectOptions){
	// store the current selections
	$(selectOptions).each(function(){
		currentSelections[$(this).attr('id')] = $(this).val();
	});
	
	// loop through each select dropdown and do the following:
	// 1. clear all disabled values
	// 2. disable currently selected values in other drop downs EXCEPT for the "Other" value
	
	$(selectOptions).each(function(i,ele){
		
	});
	$(selectOptions).each(function(i, ele){
		$(ele).find('option:disabled').attr('disabled',false);
		$.each(currentSelections,function(key,val){
			if(key != $(ele).attr('id') && val!=''){
				$(ele).find('option[value='+val+']').attr('disabled',true);
			}
		});
	});
 }



function set_visible_section_cookie() {
	var fragment = $.param.fragment();
	if ( fragment[0] == '!' ) {
		fragment = fragment.substr(1);
	}
	$.cookie('grad_view_visible', fragment, { expires: 365, path: '/' });	
}

function datatable_grad_table(elt) {
	var sortcol = 0;
	elt = $(elt)
	// look for a sort-n class indicating the sortcol
	$(elt.attr('class').split(' ')).each(function(i,cls){
		if (cls.indexOf('sort-') == 0) {
			sortcol = parseInt(cls.substr(5));
		}
	});
	elt.dataTable({
		'bPaginate': false,
	    'bInfo': false,
        'bFilter': false,
		'bLengthChange': false,
	    'bJQueryUI': true,
	    "aaSorting": [[ sortcol, "asc" ]],
	});
}

function show_section(id) {
	var elt = $('#'+id);
	if (elt.hasClass('displayed')) {
		return;
	}
	elt.removeClass('collapsed');
	elt.addClass('displayed');
	$('#'+id+'_content').html('<p><i class="fa fa-spinner fa-spin"></i></p>');

	set_visible_section_cookie()
	$.ajax({
		url: "?section="+id,
		success: function (data) {
			$('#'+id+'_content').html(data);
			prep_content();
		},
	});
}

function hide_section(id) {
	var elt = $('#'+id);
	if (elt.hasClass('collapsed')) {
		return;
	}
	elt.removeClass('displayed');
	elt.addClass('collapsed');
	$('#'+id+'_content').html('');

	set_visible_section_cookie();
}

function update_links() {
	// update all of the collapse/expand links
	var currenthash = '';
	var hash;
	$('.displayed').each(function() {
		currenthash += ',' + this.id
	});
	
	$('.displayed').each(function() {
		// set link to collapse
		hash = currenthash.replace(','+this.id, '').substr(1);
		$(this).find('a').each(function() {
			$(this).attr('href', '#!' + hash);
		});
	});
	$('.collapsed').each(function() {
		// set link to display
		hash = (currenthash + ',' + this.id).substr(1);
		$(this).find('a').each(function() {
			$(this).attr('href', '#!' + hash);
		});
	});
}

function display_sections(evnt, sectionlist) {
	// show all sections indicated by the query string
	if (!sectionlist) {
		sectionlist = $.param.fragment();
		if ( sectionlist[0] != '!') {
			return;
		}
		sectionlist = sectionlist.substr(1);
	}
	var fields = sectionlist.split(',');
	var displayed = [];
	
	$(fields).each(function (i, id) {
		if (id.length > 0) {
			show_section(id);
		}
		displayed.push(id);
	});
	$('.displayed').each(function() {
		// hide those not explicitly shown
		if(displayed.indexOf(this.id) < 0) {
			hide_section(this.id);
		}
	});
	
	update_links();
}


function prep_content() {
	$('div.datatable_container table.display').each(function(i, elt){
		elt = $(elt);
		if ( !elt.hasClass('dt_init') ) {
			datatable_grad_table(elt);
			elt.addClass('dt_init');
		}
	});
	$('.collapsiblecomment').collapsible();
	$("input#id_start_date").datepicker({
		'dateFormat' : 'yy-mm-dd'
	});
	$("input#id_date").datepicker({
		'dateFormat' : 'yy-mm-dd'
	});
	$("input#id_starting").datepicker({
		'dateFormat' : 'yy-mm-dd'
	});
}



	function getData(url) {
		$.ajax({
			type : "GET",
			url : url,
			success : function(data) {
				$("#id_content").append(data);
			}
		})
	}

	function update_from_lines() {
        if ($('#id_from_person').val() == '' ) {
            $("#id_from_lines").val('');
        } else { 
            var label = $("#id_from_person option:selected").text();
            var lines = label.split(", ");
            var from = lines.join("\r\n");
            $("#id_from_lines").val(from);
        }
	}

	var address_map = {};
	function update_to_lines() {
		var label = $("#id_address").val();
		$("#id_to_lines").val(address_map[label]);
	}

	function get_addresses(url) {
		// insert widget into form
		var prev = $('#id_date').parent().parent();
		var element = '<dt><label for="id_address">Addresses:</label></dt><dd><div class="field">';
		element += '<select id="id_address"><option value="none">&mdash;</option></select>';
		element += '<i class="fa fa-spinner fa-spin" id="fetchwait"></i></div>';
		element += '<div class="helptext">Known addresses for the student</div></dd>';
		prev.after(element)
		var id = $('#id_student').val();
		$.ajax({
			type : 'GET',
			url : url + '?id=' + id,
			error : function(data) {
				$("#fetchwait").hide();
			},
			success : function(data) {
				if(data.error !== undefined) {
					$("#fetchwait").after(' <span class="empty">Error: ' + data.error + '</span>');
					$("#fetchwait").hide();
				}
				if(data.addresses.mail !== undefined) {
					addr = data.addresses.mail;
					address_map['mail'] = addr;
					$("#id_address").append('<option value="mail">Mailing address: ' + addr.split('\n').join(', ') + '</option>')
				}
				if(data.addresses.home !== undefined) {
					addr = data.addresses.home;
					address_map['home'] = addr;
					$("#id_address").append('<option value="home">Home address: ' + addr.split('\n').join(', ') + '</option>')
				}
				$("#fetchwait").hide();
				$("#id_address").change(update_to_lines);
			}
		});
	}

function full_querystring() {
	// rebuild query string with current datatable sort
	if ( typeof query_string == 'undefined' ) {
		return;
	}
	var sort_query = $.deparam.querystring(query_string);
	var coln, dir;
	var sort='';
	
	$(table.fnSettings().aaSorting).each(function(i, col) {
		coln = col[0];
		dir = col[1][0];
		sort += ',' + coln + dir;
		
	});
    sort_query.sort = sort.substr(1);
	return $.param(sort_query, true);
}

function update_search_links() {
	// update links on this page with current datatable sort
	if ( typeof table == 'undefined' ) {
		return;
	}
	var qs = full_querystring();
	var new_url = self_url + '?' + qs;
	$('#csvlink').attr('href', new_url+"&csv=yes");
	$('#excellink').attr('href', new_url+"&excel=yes");
	$('#editlink').attr('href', new_url+"&edit_search=yes");
	$('#id_query').val(qs);
}
