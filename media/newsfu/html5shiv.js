(function(K,M){var G="3.6.2pre";
var D=K.html5||{};
var H=/^<|^(?:button|map|select|textarea|object|iframe|option|optgroup)$/i;
var C=/^(?:a|b|code|div|fieldset|h1|h2|h3|h4|h5|h6|i|label|li|ol|p|q|span|strong|style|table|tbody|td|th|tr|ul)$/i;
var Q;
var I="_html5shiv";
var A=0;
var O={};
var E;
(function(){try{var T=M.createElement("a");
T.innerHTML="<xyz></xyz>";
Q=("hidden" in T);
E=T.childNodes.length==1||(function(){(M.createElement)("a");
var V=M.createDocumentFragment();
return(typeof V.cloneNode=="undefined"||typeof V.createDocumentFragment=="undefined"||typeof V.createElement=="undefined")
}())
}catch(U){Q=true;
E=true
}}());
function F(T,V){var W=T.createElement("p"),U=T.getElementsByTagName("head")[0]||T.documentElement;
W.innerHTML="x<style>"+V+"</style>";
return U.insertBefore(W.lastChild,U.firstChild)
}function L(){var T=J.elements;
return typeof T=="string"?T.split(" "):T
}function P(T){var U=O[T[I]];
if(!U){U={};
A++;
T[I]=A;
O[A]=U
}return U
}function N(W,T,V){if(!T){T=M
}if(E){return T.createElement(W)
}if(!V){V=P(T)
}var U;
if(V.cache[W]){U=V.cache[W].cloneNode()
}else{if(C.test(W)){U=(V.cache[W]=V.createElem(W)).cloneNode()
}else{U=V.createElem(W)
}}return U.canHaveChildren&&!H.test(W)?V.frag.appendChild(U):U
}function R(V,X){if(!V){V=M
}if(E){return V.createDocumentFragment()
}X=X||P(V);
var Y=X.frag.cloneNode(),W=0,U=L(),T=U.length;
for(;
W<T;
W++){Y.createElement(U[W])
}return Y
}function S(T,U){if(!U.cache){U.cache={};
U.createElem=T.createElement;
U.createFrag=T.createDocumentFragment;
U.frag=U.createFrag()
}T.createElement=function(V){if(!J.shivMethods){return U.createElem(V)
}return N(V,T,U)
};
T.createDocumentFragment=Function("h,f","return function(){var n=f.cloneNode(),c=n.createElement;h.shivMethods&&("+L().join().replace(/\w+/g,function(V){U.createElem(V);
U.frag.createElement(V);
return'c("'+V+'")'
})+");return n}")(J,U.frag)
}function B(T){if(!T){T=M
}var U=P(T);
if(J.shivCSS&&!Q&&!U.hasCSS){U.hasCSS=!!F(T,"article,aside,figcaption,figure,footer,header,hgroup,nav,section{display:block}mark{background:#FF0;color:#000}")
}if(!E){S(T,U)
}return T
}var J={elements:D.elements||"abbr article aside audio bdi canvas data datalist details figcaption figure footer header hgroup mark meter nav output progress section summary time video",version:G,shivCSS:(D.shivCSS!==false),supportsUnknownElements:E,shivMethods:(D.shivMethods!==false),type:"default",shivDocument:B,createElement:N,createDocumentFragment:R};
K.html5=J;
B(M)
}(this,document));