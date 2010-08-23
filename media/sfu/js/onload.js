// Defaults, to be overridden.
var clf_web_names=null;
var clf_web_addrs=null;
var i=0;
var letter=null;

imp_count = 0;

images = Array(1);
link_info = Array( 'No News' );
link_href = Array( './' );

//  This is the BEST THING I've found from Dreamweaver.
function MM_findObj(n, d) { //v4.01
  var p,i,x;  if(!d) d=document; if((p=n.indexOf("?"))>0&&parent.frames.length) {
    d=parent.frames[n.substring(p+1)].document; n=n.substring(0,p);}
  if(!(x=d[n])&&d.all) x=d.all[n]; for (i=0;!x&&i<d.forms.length;i++) x=d.forms[i][n];
  for(i=0;!x&&d.layers&&i<d.layers.length;i++) x=MM_findObj(n,d.layers[i].document);
  if(!x && d.getElementById) x=d.getElementById(n); return x;
}

function MM_setTextOfLayer(objName,x,newText) { //v4.01
  if ((obj=MM_findObj(objName))!=null) with (obj)
    if (document.layers) {document.write(unescape(newText)); document.close();}
    else innerHTML = unescape(newText);
}

// This is something again from ALA.  A "Suckerfish dropdown" hack.
audience = new Object();
audience.name = "audience";
audience.transparent = true;

pullDowns = new Object();
pullDowns.name = "pullDowns";
pullDowns.transparent = false;

flyouts = Array( audience,pullDowns );

// This startlist was initially the IErepair function, less the param.  I've abstracted it to work with multiple menus on a page.  I know...  WHY???  Because that's what the client WANTS.  UGH.  These things should never be used.

function setSubULs( obj, root ) {
	if (obj==null || obj.childNodes==null) return;  // IE needs these
	if (!root && obj.nodeName=='UL') {
		if (ns){
			if (browserVersion>=5) {
				target = obj.style;
			} 
		}
		else { 
			target = obj.style;
			}
//		MyImage = new OpacityObject(target,'images/back');  // opacity for the flyouts.
//		MyImage.setBackground();
	}
	for (var i=0;i<obj.childNodes.length; i++) {
		setSubULs( obj.childNodes[i], false );
	}
}


function LoadBanner() {
	// Dynamic Banner logic:
	var bg_choice = pickRandom( banner.length );
	bannerObj = MM_findObj( 'header' );
	bannerObj.className = 'banner_'+bg_choice;
}

startFunctions = Array();  // Not needed: LoadBanner, 

startList = function() {
	for ( id in flyouts ) {
		props = flyouts[id];
		layerObject = MM_findObj( props.name );
		IErepair( layerObject );
//		if (props.transparent) setSubULs( layerObject, true );
	}/**/
	
	for ( i in startFunctions ) startFunctions[i]();
}


window.onload=startList;
