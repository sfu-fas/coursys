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

function add_to_info(key, value, tableid, rowclass) {
    // add this key/value to the info table
    var table;
    if ( typeof tableid !== 'undefined' ) {
        table = $('table#' + tableid);
    } else {
        table = $('table.info');
    }

    var cls = 'dynamic';
    if ( typeof rowclass !== 'undefined' ) {
        cls += ' ' + rowclass;
    }
    table.append('<tr class="' + cls + '"><th scope="row">' + key + '</th><td>' + value + '</td></tr>')
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
                $('#fetchwait').hide();
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
            if (data['programs']) {
                var programs = data['programs']
                var res = '';
                for (var i=0; i<programs.length; i++) {
                    res += programs[i] + '<br/>'; 
                }
                add_to_info('Programs', res);
            }
            if (data['gpa']) {
                add_to_info('CGPA', data['gpa']);
            }
            if (data['ccredits']) {
                add_to_info('Credits', data['ccredits']);
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

function get_more_info_visit(url) {
    // fetch more info on this student from SIMS
    $('#fetchwait').show();
    $.ajax({
        url: url,
        success: function(data){
            if (data['error']) {
                alert('Error: ' + data['error']);
                $('#fetchwait').hide();
                return;
            }

            if (data['programs']) {
                var programs = data['programs']
                var res = '';
                for (var i=0; i<programs.length; i++) {
                    res += programs[i] + '\n';
                }
                $('#id_programs').val(res);
            }
            if (data['gpa']) {
                $('#id_cgpa').val(data['gpa']);
            }
            if (data['ccredits']) {
                $('#id_credits').val(data['ccredits']);
            }
            if (data['gender']) {
                $('#id_gender').val(data['gender']);
            }
            if (data['citizen']) {
                $('#id_citizenship').val(data['citizen']);
            }
            $('#fetchwait').hide();
        },
        error: function(jqXHR, textStatus, errorThrown) {
			alert('Could not contact server.')
			$('#fetchwait').hide();
        }
    });
}

function more_course_info(url) {
	// fetch more info on this course from SIMS
	$('#fetchwait').show();
	$.ajax({
		url: url,
		success: function(data){
			if( $('table.info').length == 0 ) {
			    $('div.table_container').html('<table class="info" id="courseinfo"><tbody></tbody></table>');
			}
			if (data['error']) {
				add_to_info('Error', data['error'], 'courseinfo');
				$('#fetchwait').hide();
				return;
			}

			if (data['longtitle']) {
				add_to_info('Title', data['longtitle'], 'courseinfo');
			}
			if (data['shorttitle']) {
				add_to_info('Short Title', data['shorttitle'], 'courseinfo');
			}
			if (data['descrlong']) {
				add_to_info('Calendar Description', data['descrlong'], 'courseinfo');
			}
			if (data['rqmnt_designtn']) {
				add_to_info('Requirement Designation', data['rqmnt_designtn'], 'courseinfo');
			}

            $('#fetchwait').hide();
            $('#moreinfo').remove();
		},
	});
}
        			
function course_outline_info(url) {
    // fetch course outline from outlines API
    $('#fetchwait-outline').show();
    $.ajax({
		url: url,
		success: function(data){
			var anything = false;
			if (data['error']) {
				add_to_info('Error', data['error']);
				$('#fetchwait-outline').hide();
				return;
			}

			$('h2#outline').after('<p id="outlinenote">This information is from <a href="' + data['outlineurl'] + '">the course\'s outline</a>. Please see the outline itself for more complete information.</p>');
            if (data['info'] && data['info']['specialTopic']) {
				add_to_info('Special Topic', '<u>' + data['info']['specialTopic'] + '</u>', 'outlineinfo', 'linkify');
				anything = true;
			}
            if (data['info'] && data['info']['courseDetails']) {
				add_to_info('Course Details', data['info']['courseDetails'], 'outlineinfo', 'linkify');
				anything = true;
			}
            if (data['info'] && data['info']['materials']) {
				add_to_info('Material &amp; Supplies', data['info']['materials'], 'outlineinfo', 'linkify');
				anything = true;
			}
            if (data['info'] && data['info']['requirements']) {
				add_to_info('Requirements', data['info']['requirements'], 'outlineinfo', 'linkify');
				anything = true;
			}

            if (data['requiredText']) {
                var html = '<ul>';
                $(data['requiredText']).each(function(i, d){
                    html += '<li>' + d['details'] + '</li>';
                });
                html += '</ul>'
				add_to_info('Required Text', html, 'outlineinfo', 'linkify');
				anything = true;
			}

            if (data['grades']) {
                var html = '<ul>';
                $(data['grades']).each(function(i, d){
                    html += '<li>' + d['description'] + ', ' + d['weight'] + '%</li>';
                });
                html += '</ul>'
                if (data['info'] && data['info']['gradingNotes']) {
                    html += '<p>' + data['info']['gradingNotes'] + '</p>'
                }
				add_to_info('Grading', html, 'outlineinfo');
				anything = true;
			}

			$('tr.linkify td').linkify();
			if ( !anything ) {
    		    if ( data['outlineurl'] ) {
    			    $('p#outlinenote').html('See <a href="' + data['outlineurl'] + '">the course\'s outline</a> for additional information.');
			    } else {
			        $('p#outlinenote').html('Could not find <a href="http://www.sfu.ca/outlines.html">an outline</a> for this course.');
			    }
			}

			$('#fetchwait-outline').hide();
		},
	});
}

function show_titles() {
    $('.coursetitle').show();
    $('.showtitle').hide();
}
function hide_titles() {
    $('.coursetitle').hide();
    $('.showtitle').show();
}

function display_data(data) {
    const elt = $('#coursecontent');
    if (data['error']) {
        const res = '<p class="empty">Could not fetch data: ' + data['error'] + '.</p>';
        elt.html(res);
        return;
    }
    if ( data['refresh'] === 'unknown' ) {
        elt.html(`<p>The course data in the Reporting Database is of <strong>unknown age</strong>. This seems suspicious and is cause for concern.</p><p style="margin-top: 20em"><button id="ack">I understand this data is <strong>of unknown age</strong> and quality</button></p>`);
    } else {
        const refresh = new Date(data['refresh']);
        const age_hr = (new Date() - refresh) / 3600000;
        elt.html(`<p>The course data in the Reporting Database was refreshed at ${refresh.toLocaleString()}. Data is is <strong>at least</strong> that old.</p><p><button id="ack">I understand this data is <strong>${age_hr.toFixed(0)} hours</strong> old and less reliable than SIMS</button><p>`);
    }
    document.getElementById("ack").onclick = () => actually_display_data(data);
    return;
}

function actually_display_data(data) {
    const elt = $('#coursecontent');
    elt.html('');
    
    /* transfer credits */
    var html = '';
    html += '<h2 id="transfer">Transfer Credits</h2><table class="courses">';
    
    $(data.transfers).each(function(i, trns){
        html += '<tr><td>' + trns.subject + ' ' + trns.catalog_nbr + ' <span class="coursetitle">(' + trns.descr + ')</span></td><td>' + trns.units + '</td>';
        html += '<td>' + trns.grade + '</td><td>' + trns.repeat + '</td><td>' + trns.src + '</td><td>' + trns.req + '</td></tr>';
    });
    html += '</table>';
    elt.append(html);

    /* semesters and courses */
    $(data.semesters).each(function(i, sem){
        html = '';
        html += '<h2 id="s-' + sem.strm + '">' + sem.semname + ' (' + sem.career;
        if (sem.standing) {
            html += ', ' + sem.standing;
        }
        html += ')</h2>';
        html += '<table class="courses">';
        $(sem.courses).each(function(j, crs) {
            html += '<tr><td>' + crs.subject + ' ' + crs.number + ' <span class="coursetitle">(' + crs.descr + ')</span></td><td>' + crs.unit_taken + '</td>'
            html += '<td>' + crs.grade + '</td><td>' + crs.repeat + '</td><td>' + crs.req + '</td></tr>';
        });
        html += '</table>';
        elt.append(html);
        
        html = '';
        html += '<p>Term GPA: ' + sem.tgpa + '; CGPA: ' + sem.cgpa;
        if (sem.udgpa) {
            html += '; UDGPA: ' + sem.udgpa;
        }
        html += '</p>';
        elt.append(html);
    });
}

function course_data_ready(data_url) {
    $(document).ready(function() {
        $('#showlink').click(show_titles);
        $('#hidelink').click(hide_titles);
        $.ajax({
            url: data_url,
            success: display_data,
            error: function(jqXHR, textStatus, errorThrown) {
                res = '<p class="empty">Could not contact server to check for student data.</p>';
                $('#coursecontent').html(res);
            },
        });
    });
}

function student_notes_ready(student_notes_url, more_info_url, csrf_token) {
    $('.delete').click(function(){
        var id = $(this).data('id');
        $("#note-whole-"+id ).addClass('deletednote');
        $("#note-box-"+id+" .delete").hide();
        $("#note-box-"+id+" .restore").show();
        if( !show_deleted ){
            $("#note-whole-"+id).hide();
        }

        $.post(student_notes_url,
            {'csrfmiddlewaretoken': csrf_token, 'note_id': id, 'hide': 'yes'});
    });
    $('.restore').click(function(){
        var id = $(this).data('id');
        $("#note-whole-"+id ).removeClass('deletednote');
        $("#note-box-"+id+" .delete").show();
        $("#note-box-"+id+" .restore").hide();

        $.post(student_notes_url,
            {'csrfmiddlewaretoken': csrf_token, 'note_id': id, 'hide': 'no'});
    });
    $('.show_deleted').click(function(){
        show_deleted = true;
        $('.deletednote').show();
        $('.show_deleted').hide();
        $('.hide_deleted').show();
        return false;
    });
    $('.hide_deleted').click(function(){
        show_deleted = false;
        $('.deletednote').hide();
        $('.show_deleted').show();
        $('.hide_deleted').hide();
        return false;
    });

    $('#moreinfo>a').click(function() {
        get_more_info(more_info_url);
    });

    $('#advisingvisits').dataTable( {
        'bPaginate': true,
        'bInfo': false,
        'bLengthChange': true,
        "bJQueryUI": true,
        'lengthMenu': [[5, 10, 25, -1], [5, 10, 25, 'All']],
        'aaSorting': [[0, 'desc']]
    } );
}