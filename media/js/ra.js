function ra_autocomplete() {
    var regexp = /(,.*)/;
    var label;
    $('#id_person').each(function() {
        $(this).autocomplete({
            source:'/data/students',
            minLength: 2,
            select: function(event, ui){
                $(this).data("val", ui.item.value);
                label = ui.item.label.replace(regexp, "")
                $('#id_person').parent().append(document.createTextNode(" " + label));
            }
        }).bind('blur', function(){
            $(this).val($(this).data("val"))
        });
    });
}
