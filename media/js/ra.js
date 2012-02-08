function ra_autocomplete(id) {
    $('#' + id).each(function() {
        $(this).autocomplete({
            source:'/data/students',
            minLength: 2,
            select: function(event, ui){
                $(this).data("val", ui.item.value);
                $('#' + id).parent().append(document.createTextNode(" " + ui.item.label));
            }
        }).bind('blur', function(){
            $(this).val($(this).data("val"))
        });
    });

}