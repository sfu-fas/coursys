clf_web_names = Array('SFU Connect', 'Alumni Mail', 'mySFU', 'Student Information System' );

clf_web_addrs = Array('http://connect.sfu.ca', 'http://www.sfu.ca/alumni/emailforwarding/', 'http://my.sfu.ca', 'http://go.sfu.ca' );
document.write('<ul id="clf_sfu_online">');
for( i=0;i<clf_web_names.length;i++) {
	document.write( '<li><a href="'+clf_web_addrs[i]+'">'+clf_web_names[i]+'</a></li>' );
}
document.write('</ul>');
