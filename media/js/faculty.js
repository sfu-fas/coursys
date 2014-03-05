$(document).ready(function(){
  /* date pickers for date inputs */
  /* XXX: Surely we can just pick a CSS class to use instead? */
  var dates = $('#id_start_date_0, #id_end_date_0, #id_sent_date, #id_start_date, #id_end_date');
  dates.datepicker({
    dateFormat: 'yy-mm-dd',
    changeMonth: true,
    changeYear: true,
    });

  /* move template help around the page for memo template editing */
  $('#template-help').each(function() {
    $(this).css('float', 'right');
    $(this).insertBefore($('#id_template_text'));
  });

});

function Xevent_filter_update(table) {
  console.log('filter');

$.fn.dataTableExt.afnFiltering.push(function (oSettings, aData, iDataIndex) {
    return false;
});

}


function event_filter_update() {
  /* show/hide rows as appropriate on the faculty summary page */
  var cat = $('input[name=category]:checked').val();
  if ( typeof cat === "undefined" || cat == 'all' ) {
    $('#career_event_table tbody tr').show();
    //$('#scraps tr').detach().appendTo('#career_event_table tbody');
  } else {
    $('#career_event_table tbody tr').hide();
    $('#career_event_table tbody tr.' + cat).show();

    //$('#career_event_table tbody tr').detach().appendTo('#scraps');
    //$('#scraps tr.' + cat).detach().appendTo('#career_event_table tbody');

  }


/*
  $('#career_event_table').dataTable( {
    "bRetrieve": true,
  } ).fnDestroy();
  $('#career_event_table').dataTable( {
    'bPaginate': false,
    'bInfo': false,
    "aaSorting": [[2, "asc"]],
    "bJQueryUI": true,
  } );
*/
  // no zebra stripes is better than broken, for now
  $('#career_event_table tr.odd').removeClass('odd');
  $('#career_event_table tr.even').removeClass('even');

  $('#career_event_table tbody tr:visible').each( function(i, e) {
    if ( i%2 == 0 ) {
      $(e).addClass('even');
    } else {
      $(e).addClass('odd');
    }
  });

}

