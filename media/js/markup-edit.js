var help_url = '/docs/markup'; // hard-coded URL
var markup_choices = {
    'creole': 'WikiCreole',
    'markdown': 'Markdown',
    'textile': 'Textile',
    'html': 'HTML',
    'html-wysiwyg': 'HTML editor',
};
function wysiwyg_switcher(ev) {
    /* This probably fails if there is >1 .markup-content on page. */
    var val = $('.markup-content select').val();
    if ( val == 'html-wysiwyg' ) {
        tinymce.init({
            selector: '.markup-content textarea',
            plugins: ['charmap', 'code', 'codesample', 'image', 'link', 'lists', 'table'],
            toolbar: 'undo redo | bold italic strikethrough formatselect | bullist numlist | link charmap',
            block_formats: 'Paragraph=p;Header 2=h2;Header 3=h3;Header 4=h4;Block Quotation=blockquote;Preformatted Code=pre;Inline Code=code',
            formats: {
                strikethrough: {inline : 'del'},
                bold: {inline : 'strong'},
                italic: {inline : 'em'},
            }
        });
    } else {
        tinymce.remove('.markup-content textarea')
    }

    /* update help link if  */
    $('span#markup-help').html('<a href="' + help_url + '#' + val + '">' + markup_choices[val] + ' help</a>')
}
$(document).ready(function() {
	$('#id_releasedate').datepicker({'dateFormat': 'yy-mm-dd'});
	$('#id_editdate').datepicker({'dateFormat': 'yy-mm-dd'});

	$('.markup-content select').change(wysiwyg_switcher);
    wysiwyg_switcher();


} );