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

