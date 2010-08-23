function IErepair( navRoot ) {
if (navRoot==null || navRoot.childNodes==null ) return; // IE needs these
if (document.all && document.getElementById) {
for (i=0; i<navRoot.childNodes.length; i++) {
  node = navRoot.childNodes[i];
  if (node.nodeName=="LI") {
  node.onmouseover=function() {
  this.className+=" over";
    }
  node.onmouseout=function() {
  this.className=this.className.replace(" over", "");
   }
   }
  }
 }
}
