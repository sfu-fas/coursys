document.write('<a href="http://www.sfu.ca/dir/">A-Z Links</a><ul id="AtoZ">');

for( i=65;i<91;i++) {
	letter = String.fromCharCode(i+32);
	document.write( '<li><a href="http://www.sfu.ca/dir/?'+letter+'">'+letter+'</a></li>' );
}

document.write('</ul>');
