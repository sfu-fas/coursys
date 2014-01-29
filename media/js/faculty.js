$(document).ready(function(){
  var dates = $('#id_start_date, #id_end_date');
  dates.datepicker({
    dateFormat: 'yy-mm-dd',
    changeMonth: true,
    changeYear: true,
    });
});