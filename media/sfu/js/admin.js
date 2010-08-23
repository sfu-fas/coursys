// JavaScript Document

// We start with the Dreamweaver  MM_findObj function.  If you have this already, that's nice.
 
//Repetition won't hurt, but not having this function will kill you.
 
function MM_findObj(n, d) { //v4.01
  var p,i,x;  if(!d)  d=document; 
if((p=n.indexOf("?"))>0&&parent.frames.length)  {
    d=parent.frames[n.substring(p+1)].document;  n=n.substring(0,p);}
  if(!(x=d[n])&&d.all) x=d.all[n]; for  (i=0;!x&&i<d.forms.length;i++) 
x=d.forms[i][n];
   for(i=0;!x&&d.layers&&i<d.layers.length;i++)  
x=MM_findObj(n,d.layers[i].document);
  if(!x &&  d.getElementById) x=d.getElementById(n); return x;
}
// This just makes  it a LOT easier, and uses Dreamweaver's function with class.   Double-entendre beware!
function changeClass( id, newClassName )  {
 obj = MM_findObj( id  );
 obj.className=newClassName;
}

selected=null;

function swapClasses( first, second ) {
 obj1 = MM_findObj( first );
 tmp = obj1.className;
 obj2 = MM_findObj( second );
 obj1.className = obj2.className;
 obj2.className=tmp;
 obj1.swap = obj2;
 obj2.swap = obj1;
 selected = obj2;
}

function restoreSwap() {
 if (selected==null) return;
 obj1 = selected;
 selected = null;
 obj2 = obj1.swap;
 tmp = obj1.className;
 obj1.className = obj2.className;
 obj2.className=tmp;
}

function createCookie(name,value,days) {
  if (days) {
    var date = new Date();
    date.setTime(date.getTime()+(days*24*60*60*1000));
    var expires = "; expires="+date.toGMTString();
  }
  else expires = "";
  document.cookie = name+"="+value+expires+"; path=/";
}

function readCookie(name) {
  var nameEQ = name + "=";
  var ca = document.cookie.split(';');
  for(var i=0;i < ca.length;i++) {
    var c = ca[i];
    while (c.charAt(0)==' ') c = c.substring(1,c.length);
    if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
  }
  return null;
}

function LoadFn( target ) {
  if (target==null) target = 'adminPanel';
  obj = MM_findObj( target );
  obj.Size = 'max';
  obj.Pos = 'left';

  cSize = readCookie(target+"PanelSize");
  cPos = readCookie(target+"PanelPos");
  
  if (cSize!='max') MinMaxToggle( target );
  if (cPos!='left') LeftRightToggle( target );
}

function setPanelOptions( target ) {
	 if (target==null) target = 'adminPanel';
	 obj = MM_findObj( target );
	 obj.className = obj.Size+' '+obj.Pos;
}
function MinMaxToggle( target ) {
	if (!target) target = 'adminPanel';

	obj = MM_findObj( target );
	if (obj.Size=='min') obj.Size = 'max';
	else obj.Size = 'min';
	
	setPanelOptions( target );
	createCookie(target+"PanelSize",obj.Size,365 );
}

function LeftRightToggle( target ) {
 	if (target==null) target = 'adminPanel';

	obj = MM_findObj( target );
	if (obj.Pos=='right') obj.Pos='left';
	else obj.Pos = 'right';
	
	setPanelOptions( target );
	
	createCookie(target+"PanelPos",obj.Pos,365 );
}

// The end of the  Javascript
