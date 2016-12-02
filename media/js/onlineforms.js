$(document).ready(function() {
    $('.date-input').datepicker({ buttonImageOnly: true, buttonImage: '{{STATIC_URL}}images/grades/calendar.png',
                                changeMonth: true, changeYear: true,
                                dateFormat: 'yy-mm-dd', showOn: 'both'});

    // If we click submit, we want to store which button actually was clicked.
    $('input[type=submit]').click(function() {
       $submitButton = $(this)
    });
});