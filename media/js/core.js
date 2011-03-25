/* jQuery Datatables sorting by mark (e.g. "4.5/10") */
function mark_cmp(x,y) {
  xn = parseFloat(x.split("/", 1), 10)
  yn = parseFloat(y.split("/", 1), 10)
  if (isNaN(xn) && isNaN(yn)) { return 0;
  } else if (isNaN(xn)) { return -1;
  } else if (isNaN(yn)) { return 1;
  } else {
    return ((xn < yn) ? -1 : ((xn > yn) ? 1 : 0));
  }    
}
jQuery.fn.dataTableExt.oSort['by-mark-asc']  = function(x,y) { return mark_cmp(x,y) };
jQuery.fn.dataTableExt.oSort['by-mark-desc'] = function(x,y) { return mark_cmp(y,x) };

/* jQuery Datatables sorting ignoring any <a> (e.g. '<a href="foo">123</a>' sorts by '123') */
link_re = /<a href=".+">(.+)<\/a>/;
function nolink_cmp(x,y) {
  xc = link_re.exec(x);
  yc = link_re.exec(y);
  if ( xc == null && yc == null ) { return -0 }
  if ( xc == null ) { return -1; }
  if ( yc == null ) { return 1; }
  xc = xc[1];
  yc = yc[1];
  return ((xc < yc) ? -1 : ((xc > yc) ? 1 : 0));
}
jQuery.fn.dataTableExt.oSort['by-nolink-asc']  = function(x,y) { return nolink_cmp(x,y) };
jQuery.fn.dataTableExt.oSort['by-nolink-desc'] = function(x,y) { return nolink_cmp(y,x) };

/* jQuery Datatables sorting combining nolink_cmp and mark_cmp (for marks in links) */
function nolinkmark_cmp(x,y) {
  xc = link_re.exec(x)[1];
  yc = link_re.exec(y)[1];
  return mark_cmp(xc,yc);
}
jQuery.fn.dataTableExt.oSort['by-nolinkmark-asc']  = function(x,y) { return nolinkmark_cmp(x,y) };
jQuery.fn.dataTableExt.oSort['by-nolinkmark-desc'] = function(x,y) { return nolinkmark_cmp(y,x) };

/* jQuery Datatables sorting for letter grades in links */
letter_map = {"WE": 15, "WD": 15, "FX": 17, "DE": 12, "FD": 14, "GN": 16, "CN": 17, "C+": 6, "C-": 8, "A+": 0, "A-": 2, "A": 1, "C": 7, "B": 4, "AE": 17, "D": 9, "F": 11, "CC": 17, "IP": 16, "CF": 17, "N": 13, "P": 10, "AU": 17, "W": 15, "CR": 17, "B-": 5, "B+": 3} /* generated: see LETTER_POSITION in grades/models.py */
function letter_cmp(x,y) {
  xc = letter_map[x];
  yc = letter_map[y];
  if ( xc == null && yc == null ) { return 0 }
  if ( xc == null ) { return 1; }
  if ( yc == null ) { return -1; }
  return ((xc < yc) ? -1 : ((xc > yc) ? 1 : 0));
}
function nolinkletter_cmp(x,y) {
  xc = link_re.exec(x)[1];
  yc = link_re.exec(y)[1];
  return letter_cmp(xc,yc);
}
jQuery.fn.dataTableExt.oSort['by-nolinkletter-asc']  = function(x,y) { return nolinkletter_cmp(x,y) };
jQuery.fn.dataTableExt.oSort['by-nolinkletter-desc'] = function(x,y) { return nolinkletter_cmp(y,x) };

jQuery.fn.dataTableExt.oSort['by-letter-asc']  = function(x,y) { return letter_cmp(x,y) };
jQuery.fn.dataTableExt.oSort['by-letter-desc'] = function(x,y) { return letter_cmp(y,x) };

// toggle display of news item bodies
function togglenews(e, elt) {
  var event = e || window.event;
  // http://www.quirksmode.org/js/events_properties.html
  var targ, i, more;
  if (event.target) targ = event.target;
  else if (event.srcElement) targ = event.srcElement;
  if (targ.nodeType == 3) // defeat Safari bug
    targ = targ.parentNode;
  
  newsitem = targ.parentNode.parentNode;
  var divs = newsitem.getElementsByTagName('div');
  for(i=0; i<divs.length; i++) {
     if ( divs[i].className == 'newsmore' ) {
       more = divs[i];
     }
  }
  if (window.getComputedStyle(more, null).getPropertyValue('display') == 'none') {
    more.style.display = "block";
    targ.innerHTML = "-";
  } else {
    more.style.display = "none";
    targ.innerHTML = "+";
  }
}
