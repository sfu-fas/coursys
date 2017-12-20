function wysiwyg_switcher(ev) {
    if ( $('#id_markup').val() == 'html-wysiwyg' ) {
        tinymce.init({
            selector: '#id_wikitext',
            plugins: ['charmap', 'code', 'codesample', 'image', 'link', 'lists', 'table'],
            toolbar: 'undo redo | bold italic strikethrough subscript superscript formatselect | blockquote bullist numlist | link | charmap',
        });
    } else {
        tinymce.remove('#id_wikitext')
    }
}
$(document).ready(function() {
	$('#id_releasedate').datepicker({'dateFormat': 'yy-mm-dd'});
	$('#id_editdate').datepicker({'dateFormat': 'yy-mm-dd'});

	$('#id_markup').change(wysiwyg_switcher);
    wysiwyg_switcher();
} );