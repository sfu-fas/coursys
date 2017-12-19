$(document).ready(function() {
  $('pre.highlight').each(function(i, block) {
    hljs.highlightBlock(block);
  });
});