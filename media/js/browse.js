var table;

// from http://stackoverflow.com/questions/9235304/how-to-replace-the-location-hash-and-only-keep-the-last-history-entry
(function(namespace) { // Closure to protect local variable "var hash"
    if ('replaceState' in history) { // Yay, supported!
        namespace.replaceHash = function(newhash) {
            if ((''+newhash).charAt(0) !== '#') newhash = '#' + newhash;
            history.replaceState('', '', newhash);
        }
    } else {
        var hash = location.hash;
        namespace.replaceHash = function(newhash) {
            if (location.hash !== hash) history.back();
            location.hash = newhash;
        };
    }
})(window);


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
	//jQuery.bbq.pushState('!'+jQuery.param(params), 2);
	window.replaceHash('!'+jQuery.param(params));
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
            if ( typeof(v) == 'string' ) { /* one selection -> string; multiple -> array */
                v = Array(v);
            }
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
  restore_form();
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
    /* stop cache busting: http://datatables.net/forums/discussion/5714/solved-how-do-i-disable-the-cache-busting-query-parameter-that-datatables-attaches/p1 */
    'fnServerData': function ( sSource, aoData, fnCallback ) {
      /* Add some data to send to the source, and send as 'POST' */
      aoData.push( { "name": "data_type", "value": "json" } );
      $.ajax( {
        "dataType": 'json',
        "type": "GET",
        "url": sSource,
        "data": aoData,
        "success": fnCallback,
      } );
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
  //$(window).bind('hashchange', function(){restore_form();refresh();});
}

