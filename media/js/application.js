function add_course(){
    $('.course-form:hidden').first().show();
}

function init_courses() {
    // hide all course selections by default
    $('.course-form').each(function(i, e) {
        e = $(e);
        if ( e.find('select').val() ) {
            e.show();
        } else {
            e.hide();
        }
    });
}

function update(url) {
	$.ajax({
		url : url,
		success : function(data) {
			if(console && console.log) {
				console.log(data);
			}
		}
	});
}
