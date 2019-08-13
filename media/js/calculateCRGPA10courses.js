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
    // Finally, calculate the CRGPA after making these changes the first time we load.  After that, the change handler
    // should take care of this.
    calculateCRGPA();
});


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
    for (var i = 0; i < courseInputs.length; i++)
    {
        var gpa = 0;
        var credits = 0;
        if (courseInputs[i].val() != '') {
            gpa = parseFloat(courseInputs[i].val());
            credits = getCredits(courseInputs[i]);
        }
        totalCredits += credits;
        totalGP += credits * gpa;
    }
    var CGPA = totalGP / totalCredits;
    output.val(CGPA.toFixed(2));
}
