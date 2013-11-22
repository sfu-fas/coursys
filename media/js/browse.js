var table;

function server_params() {
	// build the extra GET parameters that will go in the datatables data request (by inspecting the filter form)
	var params = [];
	$('#filterform input').each(function (i, v) {
		v = $(v);
		if ( v.attr('type') == 'checkbox' ) {
			if ( v.prop('checked') ) {
				params.push({'name': v.attr('name'), 'value': v.val()});
			}
		} else {
		    if ( v.val() != '' ) {
    			params.push({'name': v.attr('name'), 'value': v.val()});
    		}
		}
	});
	$('#filterform select').each(function (i, v) {
	    v = $(v)
	    if ( v.val() != '' ) {
		    params.push({'name': v.attr('name'), 'value': $(v).val()});
		}
	});
	jQuery.bbq.pushState('!'+jQuery.param(params), 2);
	return params;
}
function restore_form() {
    // restore the state of the form from the query string
    var frag = jQuery.param.fragment();
    if ( frag.substr(0,1) != '!' ) {
        return;
    }
    var data = jQuery.deparam(frag.substr(1));
    $.each(data, function (k,v) {
        var input = $('#id_'+k);
        if ( input.length == 1 ) {
            input.val(v);
        } else {
            // try it as a checkbox
            $(v).each(function (i,cv) {
                $('input[name^="' + k + '"][value="' + cv + '"]').prop('checked', true);
            });
        }
    });
}
function refresh() {
        table.fnDraw();
}
function browser_ready(my_url) {
    table = $('#courses').dataTable( {
  	'bJQueryUI': true,
	'sPaginationType': 'full_numbers',
	'iDisplayLength' : 20,
	'aaSorting': [[0,'desc'],[1,'asc']],
        'bProcessing': true,
        'bServerSide': true,
        'sPaginationType': "full_numbers",
        'iDisplayLength' : 25,
        'sAjaxSource': my_url + '?tabledata=yes',
        'fnServerParams': function ( aoData ) {
        aoData.push.apply(aoData, server_params());
    },
  } );
  $('#filterform').change(refresh);
  $('#id_instructor').autocomplete({
        source: my_url + '?instructor_autocomplete=yes',
        minLength: 2,
        select: function(event, ui){
          $(this).val(ui.item.value);
          refresh();
        }
  });

  $(window).bind( 'hashchange', restore_form);
  restore_form();
}

