/*
This is a rather dumb set of functions.  We have gotten a request from FAS then when adding/editing an asset,
if the unit is FAS and the category is within a certain list, some non-required fields should just be hidden from
the form entirely.
 */

function hide_particular_fields() {
    // Before hiding anything, un-hide previously hidden ones.
    show_all();
    // Find out if we are in the unit we care about:
    if ($("#id_unit").children(":selected").text() === "Faculty of Applied Sciences (APSC)") {
        switch ($("#id_category").children(":selected").text()) {
            case "Swag":
            case "Brochures":
            case "Events":
            case "General":
                hide_fields(['tag', 'express_service_code', 'min_qty', 'min_vendor_qty', 'po', 'account',
                    'calibration_date', 'eol_date', 'service_records']);
                break;
            case "Electronics":
                hide_fields(['min_qty', 'min_vendor_qty', 'last_order_date', 'account', 'vendor',
                    'calibration_date', 'eol_date', 'service_records']);
                break;
            default:
                break;
        }
    }
    return;
}


/*
Two helper methods to show/hide fields by label name.  For example, the "tag" field can be hidden/shown with
hide_fields('tag').  It is really made to get a whole array to hide multiple fields,
e.g. hide_fields(['field1', 'field2, 'etc'], but it'll work either way.)
 */
function hide_fields(fields) {
    if (typeof fields === "string") {
        fields = [fields]
    }
    for (var i = 0; i < fields.length; i++)
    {
        // ensure min_qty is set to 0 if hidden, so stock status still works
        if (fields[i] == 'min_qty') { 
            $('#id_min_qty').val(0);
        }
        var real_id = 'id_' + fields[i];
        var label = $("label[for=" + real_id + "]");
        label.parent().hide();
        label.parent().next().hide();
    }
}

/*
A way to show all things within the dlform with just one call.
*/
function show_all() {
    $('.dlform').children().show();
}

$(document).ready(function() {
  $('#id_user').each(function() {
    $(this).autocomplete({
      source: '/data/students',
      minLength: 2,
      select: function(event, ui){
        $(this).data("val", ui.item.value);
      }
    });
  });
    // Every time we change one of the drop down, see if we want to change the fields.
  $("select").change(function () {
        hide_particular_fields();
  });
  // Also do the initial check based on the current dropdown values.
  hide_particular_fields();
  $('.collapse').collapsible();
});

/* All the code for server side datatables */
function inventory_browser_ready(url) {
    restore_form();
    table = $('#assets').dataTable({
        'bInfo': false,
        'bLengthChange': true,
        "bJQueryUI": true,
        'aaSorting': [[0, 'asc'], [1, 'asc']],
        'bPaginate': true,
        'processing': true,
        'serverSide': true,
        'columnDefs': [
            {
                name: 'name',
                orderable: true,
                searchable: true,
                targets: [0]
            },
            {
                name: 'qty',
                orderable: true,
                searchable: true,
                targets: [1]
            },
            {
                name: 'category',
                orderable: true,
                searchable: true,
                targets: [2]
            },
            {
                name: 'location',
                orderable: true,
                searchable: true,
                targets: [3]
            },
            {
                name: 'last_modified',
                orderable: true,
                searchable: true,
                targets: [4]
            },
            {
                name: 'stock_status',
                orderable: true,
                searchable: true,
                targets: [5]
            },
            {
                name: 'actions',
                orderable: false,
                searchable: false,
                targets: [6]
            },
        ],
        'lengthMenu': [[25, 50, 100, -1], [25, 50, 100, 'All']],
        'ajax': {
            'url': url + '?tabledata=yes',
            'type': 'GET',
            'cache': true,
            // This is stupidly repeated from core.js, but we have no choice, as the buttons don't exist when it first
            // gets called, until the data is actually returned from the server.
            'complete': function() {
                $('.confirm-submit').click(function(ev) {
                    var action = $(this).attr('data-submit-action');
                    if (action == null) {
                        action = 'complete this action'
                    }
                    return confirm("Are you sure you wish to " + action + "?");
                });
                // This finds the quantity elements we added the necessary class to and adds it to the whole row.
                $('.needsreorder').closest('tr').addClass('needsreorder');
                $('.instock').closest('tr').addClass('instock');
                $('.outofstock').closest('tr').addClass('outofstock');
            },
            'data': function (data) {
                // append all of the form filters to the query data, so we can find the server-side
                server_params().forEach(function (p) {
                    if (!(p.name in data)) {
                        data[p.name] = [];
                    }
                    data[p.name].push(p.value)
                });
                data.tabledata = 'yes';
                return data;
            }
        }
  })
  $('#filterform').change(refresh);
}


