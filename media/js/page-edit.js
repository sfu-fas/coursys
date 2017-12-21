function wysiwyg_switcher(ev) {
    if ( $('#id_markup_content_1').val() == 'html-wysiwyg' ) {
        tinymce.init({
            selector: '#id_markup_content_0',
            plugins: ['charmap', 'code', 'codesample', 'image', 'link', 'lists', 'table'],
            toolbar: 'undo redo | bold italic strikethrough subscript superscript formatselect | blockquote bullist numlist | link | charmap',
        });
    } else {
        tinymce.remove('#id_markup_content_0')
    }
}
$(document).ready(function() {
	$('#id_releasedate').datepicker({'dateFormat': 'yy-mm-dd'});
	$('#id_editdate').datepicker({'dateFormat': 'yy-mm-dd'});

	$('#id_markup_content_1').change(wysiwyg_switcher);
    wysiwyg_switcher();
} );