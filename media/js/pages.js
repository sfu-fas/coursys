function setup_tinymce(id) {
	tinyMCE.init({
		mode: "exact",
		elements: id,
		theme: "advanced",
		theme_advanced_toolbar_location: "top",
		theme_advanced_toolbar_align: "left",
		theme_advanced_statusbar_location: "bottom",
		theme_advanced_resizing: true,
		theme_advanced_buttons1: "bold,italic,sub,sup,formatselect,|,bullist,numlist,outdent,indent,|,undo,redo,|,link,unlink,|,charmap",
		theme_advanced_buttons2: "",
		theme_advanced_buttons3: "",
		theme_advanced_buttons4: "",
	});
}
function do_wysiwyg() {
	if ($('#id_markup').val() != 'wiki') {
		return;	
	}
	$('#id_markup').val('html');
	$('#wysiwyg-on').hide();
	$('#wiki-on').show();
	$.cookie('editor_pref', 'wysiwyg', { expires: 365, path: '/' });

	var current = $('#id_wikitext').val();
	$.ajax({
		url: convert_url,
		type: "POST",
		data: { data: current, to: 'html', 'csrfmiddlewaretoken': csrf_token },
	}).done(function(data) {
		var html = data['data'];
		$('#id_wikitext').val(html);
		setup_tinymce('id_wikitext');
	});
}

function do_wiki() {
	if ($('#id_markup').val() != 'html') {
		return;		
	}
	$('#id_markup').val('wiki')
	$('#wysiwyg-on').show();
	$('#wiki-on').hide();
	$.cookie('editor_pref', 'wiki	', { expires: 365, path: '/' });

	var current = $('#id_wikitext').val();
	$.ajax({
		url: convert_url,
		type: "POST",
		data: { data: current, to: "wiki", 'csrfmiddlewaretoken': csrf_token },
	}).done(function(data) {
		var wiki = data['data'];
		tinyMCE.execCommand('mceFocus', false, 'id_wikitext');
		tinyMCE.execCommand('mceRemoveControl', false, 'id_wikitext');
		$('#id_wikitext').val(wiki);
	});
}