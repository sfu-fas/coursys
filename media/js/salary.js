$(document).ready(function() {
    $("input.biweekly-input").each(function () {
        var biweeklybox = $(this);
        var annualbox = $(this).siblings('input.annual-input');
        biweeklybox.keyup(function (e) {
            var value = (parseInt(biweeklybox.val()) * 26.089285714).toFixed(2);
            annualbox.val(value);
        });
        annualbox.on('click', function () {
            biweeklybox.val('')
        });
    });
});
