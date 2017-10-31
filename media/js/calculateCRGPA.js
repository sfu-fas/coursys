/*
This is added specifically for the CMPT internal transfer application form, so that the CGPA can be calculated
automagically by the system.

This is extremely unrobust, as it depends on the IDs of the dropdowns and output not changing.  Obviously, since this
is all client-side, a clever student can also use the console to simply change the value manually.  Not much we can do
about that.  People receiving this form will have to be vigilant.
 */

$(document).ready(function() {
    var output = $("#id_10");
    // First thing to do is to disable this input to stop students from changing it.
    output.prop("readonly", true);
    // Every time we change a dropdown, recalculate the CRGPA
    $("select").change(function () { calculateCRGPA(); });
    // Run it once so the value is there, just in the ridiculously low possibility that the defaults are correct
    // for some student.
    calculateCRGPA();
});


/* All courses except these 2 are 3 credits. */
function getCredits(selector) {
    switch (selector.children(":selected").text().toUpperCase()) {
        case "CMPT 275":
            return 4;
        case "MATH 150":
            return 4;
        default:
            return 3;
    }
}

/* The value is already in the drop down, just make sure it"s a float. */
function getGPAValue(selector) {
    return parseFloat(selector.val());
}

function calculateCRGPA() {
    var courseInputs = [$("#id_4"), $("#id_6"), $("#id_8")];
    var gradeInputs = [$("#id_5"), $("#id_7"), $("#id_9")];
    var output = $("#id_10");
    var totalCredits = 0;
    var totalGP = 0.00;
    for (var i = 0; i < courseInputs.length; i++)
    {
        var credits = getCredits(courseInputs[i]);
        var gpa = getGPAValue(gradeInputs[i]);
        totalCredits += credits;
        totalGP += credits * gpa;
    }
    var CGPA = totalGP / totalCredits;
    output.val(CGPA.toFixed(2));
}