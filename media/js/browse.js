var table;

function build_calendar(url, start) {
	$('#calendar').fullCalendar({
    	header: {
      		left: 'prev,next today',
	      	center: 'title',
      		right: 'month,agendaWeek'
    	},
    	events: {
      		url: url,
	      	cache: true,
      		ignoreTimezone: false,
    	},
    	height: 500,
    	firstHour: 8,
    	slotMinutes: 60,
    	defaultView: 'agendaWeek',
        defaultDate: start
  	})
}

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
        if (input.prop("tagName") == 'SPAN') { // multi-select checkboxes
            if ( Array.isArray(v) ) {
                $.each(v, function(kk, vv) {
                    $('input[name^="' + k + '"][value="' + vv + '"]').prop('checked', true);
                });
            } else {
                $('input[name^="' + k + '"][value="' + v + '"]').prop('checked', true);
            }
        } else {
            input.val(v);
        }
    });
}
function refresh() {
  table.fnDraw();
}

function browser_ready(my_url) {
  restore_form();
  table = $('#courses').dataTable( {
    'jQueryUI': true,
    'pagingType': 'full_numbers',
    'pageLength' : 20,
    'order': [[0,'desc'],[1,'asc']],
    'processing': true,
    'serverSide': true,
    'columns': [
        null,
        null,
        null,
        null,
        {'orderable': false},
        null,
    ],
    'ajax': {
        'url': my_url,
        'type': 'GET',
        'cache': true,
        'data': function (data) {
            // append all of the form filters to the query data, so we can find the server-side
            server_params().forEach(function(p) {
                if (!(p.name in data)) {
                    data[p.name] = [];
                }
                data[p.name].push(p.value)
            });
            data.tabledata = 'yes';
            return data;
        }
    }
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
  $('#filterform').tooltip();
  $('table#courses thead').tooltip();
}

