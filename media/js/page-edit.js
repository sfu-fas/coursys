function wysiwyg_switcher(ev) {
    /* This probably fails if there is >1 .markup-content on page. */
    if ( $('.markup-content select').val() == 'html-wysiwyg' ) {
        tinymce.init({
            selector: '.markup-content textarea',
            plugins: ['charmap', 'code', 'codesample', 'image', 'link', 'lists', 'table'],
            toolbar: 'undo redo | bold italic strikethrough subscript superscript formatselect | blockquote bullist numlist | link | charmap',
        });
    } else {
        tinymce.remove('.markup-content textarea')
    }
}
$(document).ready(function() {
	$('#id_releasedate').datepicker({'dateFormat': 'yy-mm-dd'});
	$('#id_editdate').datepicker({'dateFormat': 'yy-mm-dd'});

	$('.markup-content select').change(wysiwyg_switcher);
    wysiwyg_switcher();
} );