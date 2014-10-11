
// enable or disable ordering of activities for instructor: disable if not sorted by position.
function enable_disable_ordering(oSettings) {
  var s = oSettings.aaSorting;
  // condition is essentially (oSettings.aaSorting == [[0,"asc",...]])
  if ( s.length==1 && s[0].length>=2 && s[0][0]==0 && s[0][1]=='asc' ) {
    // sorted by position: enable reordering buttons
    $('.arrow_up').show();
    $('.arrow_down').show();
  } else {
    $('.arrow_up').hide();
    $('.arrow_down').hide();
  }
}

function swap_contents(e1, e2) {
    // swap the contents of the two jquery elements
    var c1 = e1.contents();
    var c2 = e2.contents();
    c1.detach();
    c2.detach();
    e1.append(c2);
    e2.append(c1);
}


function reorder_activities(url, csrf_token, table, tr1, tr2) {
    // swap the positions of the activities represented by these two rows; and swap on-page.
	var id_1 = tr1.attr('id').substr(9);
	var id_2 = tr2.attr('id').substr(9);

	$.post(url,
	    {'id_up': id_1, 'id_down': id_2, 'csrfmiddlewaretoken': csrf_token},
	    function(data) {
	        // swap the rows to reflect DB change, but keep the ordering <td> stationary for the same reason
	        var sort1 = tr1.find('.sortarrows');
	        var sort2 = tr2.find('.sortarrows');
	        swap_contents(tr1, tr2);
	        var tmpid = tr1.attr('id');
	        tr1.attr('id', tr2.attr('id'));
	        tr2.attr('id', tmpid);
	        swap_contents(sort1, sort2);
	    }
	);

}
