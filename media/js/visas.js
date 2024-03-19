var table;

function handle_form_change() {
  table.fnDraw();
}

function visa_browser_setup(my_url) {
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
    'fnRowCallback': function( row ) {
        $('.visaexpired', row).closest('tr').addClass('visaexpired');
        $('.visaalmostexpired', row).closest('tr').addClass('visaalmostexpired');
        $('.visavalid', row).closest('tr').addClass('visavalid');
    },
  } );
}