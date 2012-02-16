function ra_autocomplete(id) {
    var regexp = /(,.*)/;
    var label;
    $('#' + id).each(function() {
        $(this).autocomplete({
            source:'/data/students',
            minLength: 2,
            select: function(event, ui){
                $(this).data("val", ui.item.value);
                label = ui.item.label.replace(regexp, "")
                $('#' + id).parent().append(document.createTextNode(" " + label));
            }
        }).bind('blur', function(){
            $(this).val($(this).data("val"))
        });
    });
}