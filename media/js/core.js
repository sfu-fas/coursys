/* jQuery Datatables sorting by mark (e.g. "4.5/10") */
function mark_cmp(x,y) {
  xn = parseFloat(x.split("/", 1), 10)
  yn = parseFloat(y.split("/", 1), 10)
  if (isNaN(xn) && isNaN(yn)) { return 0;
  } else if (isNaN(xn)) { return 1;
  } else if (isNaN(yn)) { return -1;
  } else {
    return ((xn < yn) ?  1 : ((xn > yn) ? -1 : 0));
  }    
}
/* Define two custom functions (asc and desc) for string sorting */
jQuery.fn.dataTableExt.oSort['by-mark-asc']  = function(x,y) { return mark_cmp(x,y) };
jQuery.fn.dataTableExt.oSort['by-mark-desc'] = function(x,y) { return mark_cmp(y,x) };

