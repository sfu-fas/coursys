/*
This is added specifically for the CMPT internal transfer application form, so that the CGPA can be calculated
automagically by the system.

This is extremely unrobust, as it depends on the IDs of the dropdowns and output not changing.  Obviously, since this
is all client-side, a clever student can also use the console to simply change the value manually.  Not much we can do
about that.  People receiving this form will have to be vigilant.

This is the new 10-course version, without equivalencies.  The old file was calculateCRGPA.js
 */

$(document).ready(function() {
    var output = $("#id_13");
    // First thing to do is to disable this input to stop students from changing it.
    output.prop("readonly", true);
    // Every time we change a dropdown, recalculate the CRGPA
    $("select").change(function () {
        calculateCRGPA();
    });
    // Also check submit button conditions when the CGPA input text changes
    $("#id_14").on('input', function() {
        calculateCRGPA();
    });
    // Finally, calculate the CRGPA after making these changes the first time we load.  After that, the change handler
    // should take care of this.
    calculateCRGPA();
    $('.submit[name="submit"]').tooltip();
});


function disableSubmit(title) {
    var submitButton = $('.submit[name="submit"]');
    submitButton.attr('disabled', true);
    submitButton.attr('title', title);
}

function enableSubmit() {
    var submitButton = $('.submit[name="submit"]');
    submitButton.attr('disabled', false);
    submitButton.attr('title', '');
}

function checkConditions(selectedCourses) {
    var titleString = 'You cannot submit this form for the following reason(s): \n';
    var problemsFound = false;
    if (selectedCourses < 3) {
        problemsFound = true;
        titleString += 'You have added grades for less than 3 courses.\n'
    }
    if (output.val() < 2.67) {
        problemsFound = true;
        titleString += 'Your CRGPA is below 2.67.\n'
    }
    if ($("#id_14").val() < 2.4) {
        problemsFound = true;
        titleString += 'Your CGPA is below 2.40.\n'
    }
    if ($("#id_15").val() != 'choice_1') {
        problemsFound = true;
        titleString += 'You have selected that you do not have at least two CMPT courses and one MACM course.\n'
    }
    if ($("#id_16").val() != 'choice_1') {
        problemsFound = true;
        titleString += 'You have selected that you have not completed at least two of the above courses at SFU.\n'
    }
    if ($("#id_17").val() != 'choice_1') {
        problemsFound = true;
        titleString += 'You have selected that you did not provide the first grade for a repeated course.\n'
    }
    if (problemsFound) {
        disableSubmit(titleString);
    }
    else {
        enableSubmit();
    }
}

/* All courses except these 2 are 3 credits. */
function getCredits(selector) {
    if (selector.attr("id") === "id_6") {
        return 4;
    }
    else {
        return 3;
    }
}


function calculateCRGPA() {
    var courseInputs = [$("#id_4"), $("#id_5"), $("#id_6"), $("#id_7"), $("#id_8"), $("#id_9"), $("#id_10"), $("#id_11"), $("#id_12")];
    var output = $("#id_13");
    var totalCredits = 0;
    var totalGP = 0.00;
    var selectedCourses = 0;
    for (var i = 0; i < courseInputs.length; i++)
    {
        var gpa = 0;
        var credits = 0;
        if (courseInputs[i].val() !== '') {
            gpa = parseFloat(courseInputs[i].val());
            credits = getCredits(courseInputs[i]);
            selectedCourses += 1;
        }
        totalCredits += credits;
        totalGP += credits * gpa;
    }
    var CGPA = totalGP / totalCredits;
    if (isNaN(CGPA)) {
        output.val('');
    }
    else {
        output.val(CGPA.toFixed(2));
    }
    // Every time we recalculate this, check the conditions that check if we should enable/disable the submit button.
    checkConditions(selectedCourses);
}
