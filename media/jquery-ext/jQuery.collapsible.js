/**
 * --------------------------------------------------------------------
 * jQuery collapsible plugin
 * Author: Scott Jehl, scott@filamentgroup.com
 * Copyright (c) 2009 Filament Group 
 * licensed under MIT (filamentgroup.com/examples/mit-license.txt)
 * --------------------------------------------------------------------
 */
$.fn.collapsible = function(){
	return $(this).each(function(){
	
		//define
		var collapsibleHeading = $(this);
		var collapsibleContent = collapsibleHeading.next();
		
		//modify markup & attributes
        // classam - href="#" can cause the document to jump to the top
        //           in some browsers,
        //           so I've replaced it with #hi-there, which doesn't do this
		collapsibleHeading.addClass('collapsible-heading')
			.prepend('<span class="collapsible-heading-status"></span>')
			.wrapInner('<a href="#hi-there" class="collapsible-heading-toggle"></a>');
			
		collapsibleContent.addClass('collapsible-content');
		
		//events
		collapsibleHeading	
			.bind('collapse', function(){
				$(this)
					.addClass('collapsible-heading-collapsed')
					.find('.collapsible-heading-status').text('Show ');
										
				collapsibleContent.slideUp(0, function(){
					$(this).addClass('collapsible-content-collapsed').removeAttr('style').attr('aria-hidden',true);
				});
			})
			.bind('collapse_slow', function(){
				$(this)
					.addClass('collapsible-heading-collapsed')
					.find('.collapsible-heading-status').text('Show ');
										
				collapsibleContent.slideUp('slow', function(){
					$(this).addClass('collapsible-content-collapsed').removeAttr('style').attr('aria-hidden',true);
				});
			})
			.bind('expand', function(){
				$(this)
					.removeClass('collapsible-heading-collapsed')
					.find('.collapsible-heading-status').text('Hide ');
										
				collapsibleContent
					.slideDown(0, function(){
						$(this).removeClass('collapsible-content-collapsed').removeAttr('style').attr('aria-hidden',false);
					});
			})
			.click(function(){ 
				if( $(this).is('.collapsible-heading-collapsed') ){
					$(this).trigger('expand'); 
				}	
				else {
					$(this).trigger('collapse'); 
				}
				return false;
			})
			.trigger('collapse');

		collapsibleHeading.find('a').click(function() {
			window.location = this.href;
		});
	});	
};	
