$(document).ready(function() {
    $('.date-input').datepicker({ buttonImageOnly: true, buttonImage: '/static/images/grades/calendar.png',
                                changeMonth: true, changeYear: true,
                                dateFormat: 'yy-mm-dd', showOn: 'both'});

    // If we click submit, we want to store which button actually was clicked.
    $('input[type=submit]').click(function() {
       $submitButton = $(this)
    });

});

function confirmDelete() {
        return confirm("Are you sure you want to mark this form done?  This will prevent any more interaction with this form.");
}
