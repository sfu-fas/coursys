$(document).ready(function(){
  /* date pickers for date inputs */
  var dates = $('.date-input');
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

  /* grant owners multiselect */
  $("#id_owners").css("min-height", "180px").multiselect();

});

function event_filter_update(datatable) {
  if ( $('input:radio[name=category]').length == 0 ) {
    // if form hidden, don't filter
    return;
  }

  var cat = $('input:radio[name=category]:checked').val();
  var table = $('#' + datatable).dataTable( {
    "bRetrieve": true,
  } );

  $.fn.dataTableExt.afnFiltering = [];
  $.fn.dataTableExt.afnFiltering.push(function (oSettings, aData, iDataIndex) {
    if ( oSettings.nTable.id != datatable ) {
      return true;
    }

    var row = $(table.fnGetNodes(iDataIndex));
    if ( cat === 'all' ) {
      return true;
    } else if ( row.hasClass(cat) ) {
      return true;
    } else {
      return false;
    }
  });

  table.fnDraw();
}
