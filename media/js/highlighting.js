$(document).ready(function() {
  $('pre[lang]').each(function(i, block) {
    /* adapt the github markdown output to look like creole */
    block = $(block);
    lang = block.attr('lang');
    block.addClass('highlight');
    block.addClass('lang-'+lang);
  });
  $('pre.highlight').each(function(i, block) {
    hljs.highlightBlock(block);
  });
});