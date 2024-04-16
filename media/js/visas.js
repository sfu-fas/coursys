var table;

function handle_form_change() {
  table.fnDraw();
}

function visa_browser_setup(my_url) {
  $("#id_start_date").datepicker({'dateFormat': 'yy-mm-dd'});
  table = $('#visa_table').dataTable( {
    'jQueryUI': true,
    'pagingType': 'full_numbers',
    'pageLength' : 25,
    'processing': true,
    'serverSide': true,
    'scrollY': false, 
    'columnDefs': [
      { "orderable": false, "targets": 6 },
      { "width": "32%", "targets": 0 },
      { "width": "10%", "targets": 1 },
      { "width": "10%", "targets": 2 },
      { "width": "10%", "targets": [3, 4] },
      { "width": "14%", "targets": [5, 6] },
  ],
    'sAjaxSource': my_url + '?tabledata=yes',
    'fnServerData': function ( sSource, aoData, fnCallback ) {
      if ( $('#id_type').val() != 'all' ) {
        aoData.push( { "name": "type", "value": $('#id_type').val() } );
      }
      if ( $('#id_start_date').val() != '' ) {
        aoData.push( { "name": "start_date", "value": $('#id_start_date').val() } );
      }
      if ( $('input:radio[name=hide_expired]:checked').val() != '' ) {
        aoData.push( { "name": "hide_expired", "value": $('input:radio[name=hide_expired]:checked').val() } );
      }
      if ( $('#id_unit').val() != 'all' ) {
        aoData.push( { "name": "unit", "value": $('#id_unit').val() } );
      }
      $.getJSON( sSource, aoData, function (json) {
        fnCallback(json);
      } );
    },
    'fnRowCallback': function( row ) {
        $('.visaexpired', row).closest('tr').addClass('visaexpired');
        $('.visaalmostexpired', row).closest('tr').addClass('visaalmostexpired');
        $('.visavalid', row).closest('tr').addClass('visavalid');
    },
  } );
  $('#filterform').change(handle_form_change);
}