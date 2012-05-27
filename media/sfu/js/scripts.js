var onlineJSON = "/media/sfu/js/online.json"; 

function AtoZ(){
    var atoz = '';
    for( i=65;i<91;i++){
        letter = String.fromCharCode(i+32);
        atoz +='<li><a href="http://www.sfu.ca/dir/?'+letter+'">'+letter+'</a></li>';
    }
    jQuery('<ul>').html(atoz).attr('id','AtoZ').css('zIndex', 999).appendTo('li#directory');
};

function online(jsonData){

    var data = jsonData;
    var menu = '';
    
    for (var i= 0; i < data.services.length; i++) {
        menu += '<li><a href="'+data.services[i].link+'">'+data.services[i].label+'</a></li>';
    }
    
    jQuery('<ul>').html(menu).attr('id','onlineServices').css('zIndex', 1000).appendTo('#online');

};

(function($) {
    $(document).ready(function(){
        //Calling AtoZ function (creates A to Z menu)
        AtoZ();
        
        $(function() {
        //Loading the JSON for the SFU Online Menu of the Website
            $.getJSON(onlineJSON,
            function(jsonData){
                online(jsonData);
            });
        });
    
        $('li.dropdown').hover(
            function() { $('ul', this).css('display', 'block'); },
            function() { $('ul', this).css('display', 'none'); }
        );
        
        $('#directory').hover(
            function() { $('#directory a.tabs').css('border-bottom', '10px solid #cb5a60'); },
            function() { $('#directory a.tabs').css('border-bottom', 'none'); }
        );
        
        $('#online').hover(
            function() { $('#online a.tabs').css('border-bottom', '10px solid #cb5a60'); },
            function() { $('#online a.tabs').css('border-bottom', 'none'); }
        );
        
        $("#s").focus(function() {
            if( this.value == this.defaultValue ){
                this.value = "";
            }
        }).blur(function() {
            if( !this.value.length ) {
                this.value = this.defaultValue;
            }
        });

        /* Zebra tables */
        $('div.alternate table tr:even').css('background-color','#ddd');
        $('div.alternate table tr:odd').css('background-color','#eee');
        $('div.alternate table th').css('background-color','#fff');
    }); // End $(document).ready(function(){
})(jQuery);
