$(document).ready(function() {
	$("input.semester-input").each(function() {
		var semesterbox = $(this);
		var semesterstart = semesterbox.hasClass("semester-start");
		var datebox = $(this).siblings('input.date-input');
		semesterbox.keyup(function(e) {
			var value = semesterbox.val();
			if (value.toString().length == 4) {
				var base = 1900;
				var year = base + parseInt(value.toString().slice(0, 3));
				var sm = parseInt(value.toString().slice(3));
				if (sm == 1) {
					var start = year + '-01-01';
					var end = year + '-04-30';
				}
				else if (sm == 4) {
					var start = year + '-05-01';
					var end = year + '-08-31';
				}
				else if (sm == 7) {
					var start = year + '-09-01';
					var end = year + '-12-31';
				}
				else {
					semesterbox.toggleClass("error");
				}

				if (semesterstart == true) {
					datebox.val(start);
				}
				else {
					datebox.val(end);
				}
			}
		});
		datebox.keyup(function(e) {
			semesterbox.val('');
		});		
	});
});