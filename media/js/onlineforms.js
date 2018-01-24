function update_list_input_visible(div) {
    // update display of list entry inputs so the 'current' number are displayed
    if ( div.current < div.min ) {
        div.current = div.min;
    }
    if ( div.current > div.max ) {
        div.current = div.max;
    }
    var n = div.current;
    div.find('input').each(function(i, input) {
        if (i > n-1) {
            input.style.display = 'none';
            input.value = '';
        } else {
            input.style.display = 'block';
        }
    });

    div.find('.removebutton').prop('disabled', div.current === div.min);
    div.find('.addbutton').prop('disabled', div.current === div.max);
}

function init_list_input(i, div) {
    // initialize a "enter list of things" input
    div = $(div);
    var name = div.attr('data-name');
    var min = parseInt(div.attr('data-min'));
    var max = parseInt(div.attr('data-max'));
    div.current = min;

    div.find('input').each(function(i, input) {
        if ( input.value.length > 0 ) {
           div.current = Math.max(div.current, i+1);
        }
    });

    div.min = min;
    div.max = max;

    var button = $('<button class="removebutton">Remove item</button>');
    button.click(function() {
        div.current -= 1;
        update_list_input_visible(div);
        return false;
    });
    div.append(button);

    button = $('<button class="addbutton">Add item</button>');
    button.click(function() {
        div.current += 1;
        update_list_input_visible(div);
        return false;
    });
    div.append(button);

    update_list_input_visible(div);
}

$(document).ready(function() {
    $('.date-input').datepicker({ dateFormat: 'yy-mm-dd' });
    $('div.list-input').each(init_list_input);
    // If we click submit, we want to store which button actually was clicked.
    $('input[type=submit]').click(function() {
       $submitButton = $(this)
    });
});

function confirmDelete() {
        return confirm("Are you sure you want to mark this form done?  This will prevent any more interaction with this form.");
}
