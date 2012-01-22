$(function(){
	$('#id_base_units').change(function(){
		if($(this).val()<=0){
			alert("Base units cannot be negative!");
		}
		$('#maxHours').html($(this).val()*42);
		
	});
	$('#maxHours').html($('#id_base_units').val()*42);
	
});
