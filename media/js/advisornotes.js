
function add_to_info(key, value) {
    $('table.info').append('<tr class="dynamic"><th class="ui-state-default">' + key + '</th><td>' + value + '</td></tr>')
}

function get_more_info(url) {
    $('#fetchwait').show();
    $.ajax({
        url: url,
        success: function(data){
            $('table.info tr.dynamic').remove();
            if (data['error']) {
                alert('Error: ' + data['error']);
                return;
            }

            if (data['addresses']) {
                $.each(data['addresses'], function(key, value) {
                    value = value.replace('\n', '<br/>')
                    add_to_info('Address (' + key + ')', value);
                });
            }
            if (data['phones']) {
                $.each(data['phones'], function(key, value) {
                    add_to_info('Phone (' + key + ')', value);
                });
            }
            if (data['gender']) {
                add_to_info('Gender', data['gender']);
            }
            if (data['citizen']) {
                add_to_info('Citizenship', data['citizen']);
            }
            if (data['visa']) {
                add_to_info('Visa', data['visa']);
            }
            $('#fetchwait').hide();
            $('#moreinfo').remove();
        }
    });
}