//---------------------------------------------------------------
// Opacity Displayer, Version 1.0
// Copyright Michael Lovitt, 6/2002.
// Distribute freely, but please leave this notice intact.
//---------------------------------------------------------------

//---------------------------------------------------------------
// OPACITY OBJECT
//
// Instantiates the object, defines the properties and methods.

function OpacityObject(div, strPath) {
	this.layerObject = div;
	this.path = strPath;
/*	if (ns){
		if (browserVersion>=5) {
			this.layerObject = document.getElementById(divId).style;
		} else { 
			this.layerObject = eval("document."+divId);
		}
	} else {
		this.layerObject = eval(divId + ".style");
	}/**/
	this.setBackground = od_object_setBackground;
}
// Uses AlphaImageLoader filter, or the css background property,
// as appropriate, to apply a PNG or GIF as the background of the layerObject.
function od_object_setBackground() {
	if (pngAlpha) {
		this.layerObject.filter = "progid:DXImageTransform.Microsoft.AlphaImageLoader(src='"+this.path+".png', sizingMethod='scale')";
	} else if (pngNormal) {
		if (browser.isMac && browser.isIE5up ) this.layerObject.backgroundColor = '#999999';
		else this.layerObject.backgroundImage = 'url('+this.path+'.png)';
	} else {
		this.layerObject.backgroundImage = 'url('+this.path+'.gif)';
	}
}
//---------------------------------------------------------------

//---------------------------------------------------------------
// OPACITY DISPLAY FUNCTION
// Outputs the image as a div with the AlphaImageLoader, or with
// a standard image tag.
function od_displayImage(strId, strPath, intWidth, intHeight, strClass, strAlt) {	
	if (pngAlpha) {
		document.write('<div style="height:'+intHeight+'px;width:'+intWidth+'px;filter:progid:DXImageTransform.Microsoft.AlphaImageLoader(src=\''+strPath+'.png\', sizingMethod=\'scale\')" id="'+strId+'" class="'+strClass+'"></div>');
	} else if (pngNormal) {
		document.write('<img src="students/%27%2BstrPath%2B%27.png" width="'+intWidth+'" height="'+intHeight+'" name="'+strId+'" border="0" class="'+strClass+'" alt="'+strAlt+'" />');
	} else {
		document.write('<img src="students/%27%2BstrPath%2B%27.gif" width="'+intWidth+'" height="'+intHeight+'" name="'+strId+'" border="0" class="'+strClass+'" alt="'+strAlt+'" />');
	}
}
//---------------------------------------------------------------

//---------------------------------------------------------------
// OPACITY ROLL-OVER FUNCTIONS
function od_rollOver(strId, strColor) {	
	if (pngAlpha) {
		document.getElementById(strId).style.backgroundColor = strColor;
	} else {
	    if (document.images && (flag == true)) {
	        document[strId].src = eval(strId + "on.src");
	    }
	}
}
function od_rollOut(strId, strColor) {	
	if (pngAlpha) {
		document.getElementById(strId).style.backgroundColor = strColor;
	} else {
	    if (document.images) {
	        document[strId].src = eval(strId + "off.src");
	    }
	}
}
//---------------------------------------------------------------

//---------------------------------------------------------------
// global variables

// if IE5.5+ on win32, then display PNGs with AlphaImageLoader
if ((browser.isIE55 || browser.isIE6up) && browser.isWin32) {
	var pngAlpha = true;
	var strExt = ".png";
// else, if the browser can display PNGs normally, then do that. that list includes:
	//     -Gecko Engine: Netscape 6 or Mozilla, Mac or PC
	//     -IE5+ Mac (OpacityObject applies the background image at 100% opacity)
	//     -Opera 6+ PC
	//     -Opera 5+ Mac (Doesn't support dynamically-set background images)
	//     -Opera 6+ Linux 
	//     -Omniweb 3.1+ 
	//     -Icab 1.9+ 
	//     -WebTV 
	//     -Sega Dreamcast
} else if ((browser.isGecko) || (browser.isIE5up && browser.isMac) || (browser.isOpera && browser.isWin && browser.versionMajor >= 6) || (browser.isOpera && browser.isUnix && browser.versionMajor >= 6) || (browser.isOpera && browser.isMac && browser.versionMajor >= 5) || (browser.isOmniweb && browser.versionMinor >= 3.1) || (browser.isIcab && browser.versionMinor >= 1.9) || (browser.isWebtv) || (browser.isDreamcast)) {
	var pngNormal = true;
	var strExt = ".png";
	// otherwise, we use plain old GIFs
} else {
	var strExt = ".gif";
}

var ns = (document.all)?false:true;
var browserVersion = parseFloat(navigator.appVersion );
//---------------------------------------------------------------
