function search_sims(url, emplid, formurl, csrftoken) {
    // for not-found student, do SIMS search and report result (with form to add if relevant)
    $('#fetchwait').show();
    $.ajax({
        url: url + '?emplid=' + emplid,
        success: function(data){
            if (data['error']) {
                res = '<p class="empty">Problem when checking SIMS for missing student data: ' + data['error'] + '.</p>';
            } else {
                res = '<form action="' + formurl + '" method="post">' + csrftoken
                res += '<input type="hidden" name="emplid" value="' + emplid + '" />'
                res += '<p>Student number found in SIMS: ' + data['last_name'] + ', ' + data['first_name']
                if (data['userid']) {
                    res += ', ' + data['userid']
                }
                res += '. <input type="submit" value="Add From SIMS"/></p></form>'
            }
            $('#simsresult').append(res);
            $('#fetchwait').hide();
        },
        error: function(jqXHR, textStatus, errorThrown) {
			res = '<p class="empty">Could not contact server to check for missing student data.</p>';
			$('#simsresult').append(res);
			$('#fetchwait').hide();    	
        }
    });
}

function add_to_info(key, value) {
    // add this key/value to the info table
    $('table.info').append('<tr class="dynamic"><th class="ui-state-default">' + key + '</th><td>' + value + '</td></tr>')
}

function get_more_info(url) {
    // fetch more info on this student from SIMS
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
        },
        error: function(jqXHR, textStatus, errorThrown) {
			alert('Could not contact server.')
			$('#fetchwait').hide();    	
        }
    });
}