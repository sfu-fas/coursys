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
  xc = link_re.exec(x)[1];
  yc = link_re.exec(y)[1];
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

