/* Respond.js v1.1.0: min/max-width media query polyfill. (c) Scott Jehl. MIT/GPLv2 Lic. j.mp/respondjs  */
(function(E){E.respond={};
respond.update=function(){};
respond.mediaQueriesSupported=E.matchMedia&&E.matchMedia("only all").matches;
if(respond.mediaQueriesSupported){return 
}var W=E.document,S=W.documentElement,I=[],K=[],Q=[],O={},H=30,F=W.getElementsByTagName("head")[0]||S,G=W.getElementsByTagName("base")[0],B=F.getElementsByTagName("link"),D=[],A=function(){var d=B,Y=d.length,b=0,a,Z,c,X;
for(;
b<Y;
b++){a=d[b],Z=a.href,c=a.media,X=a.rel&&a.rel.toLowerCase()==="stylesheet";
if(!!Z&&X&&!O[Z]){if(a.styleSheet&&a.styleSheet.rawCssText){M(a.styleSheet.rawCssText,Z,c);
O[Z]=true
}else{if((!/^([a-zA-Z:]*\/\/)/.test(Z)&&!G)||Z.replace(RegExp.$1,"").split("/")[0]===E.location.host){D.push({href:Z,media:c})
}}}}U()
},U=function(){if(D.length){var X=D.shift();
N(X.href,function(Y){M(Y,X.href,X.media);
O[X.href]=true;
setTimeout(function(){U()
},0)
})
}},M=function(k,X,Z){var g=k.match(/@media[^\{]+\{([^\{\}]*\{[^\}\{]*\})+/gi),l=g&&g.length||0,X=X.substring(0,X.lastIndexOf("/")),Y=function(i){return i.replace(/(url\()['"]?([^\/\)'"][^:\)'"]+)['"]?(\))/g,"$1"+X+"$2$3")
},a=!l&&Z,d=0,c,e,f,b,h;
if(X.length){X+="/"
}if(a){l=1
}for(;
d<l;
d++){c=0;
if(a){e=Z;
K.push(Y(k))
}else{e=g[d].match(/@media *([^\{]+)\{([\S\s]+?)$/)&&RegExp.$1;
K.push(RegExp.$2&&Y(RegExp.$2))
}b=e.split(",");
h=b.length;
for(;
c<h;
c++){f=b[c];
I.push({media:f.split("(")[0].match(/(only\s+)?([a-zA-Z]+)\s?/)&&RegExp.$2||"all",rules:K.length-1,hasquery:f.indexOf("(")>-1,minw:f.match(/\(min\-width:[\s]*([\s]*[0-9\.]+)(px|em)[\s]*\)/)&&parseFloat(RegExp.$1)+(RegExp.$2||""),maxw:f.match(/\(max\-width:[\s]*([\s]*[0-9\.]+)(px|em)[\s]*\)/)&&parseFloat(RegExp.$1)+(RegExp.$2||"")})
}}J()
},L,R,V=function(){var Z,a=W.createElement("div"),X=W.body,Y=false;
a.style.cssText="position:absolute;font-size:1em;width:1em";
if(!X){X=Y=W.createElement("body");
X.style.background="none"
}X.appendChild(a);
S.insertBefore(X,S.firstChild);
Z=a.offsetWidth;
if(Y){S.removeChild(X)
}else{X.removeChild(a)
}Z=P=parseFloat(Z);
return Z
},P,J=function(j){var X="clientWidth",b=S[X],h=W.compatMode==="CSS1Compat"&&b||W.body[X]||b,d={},g=B[B.length-1],Z=(new Date()).getTime();
if(j&&L&&Z-L<H){clearTimeout(R);
R=setTimeout(J,H);
return 
}else{L=Z
}for(var e in I){var l=I[e],c=l.minw,k=l.maxw,a=c===null,m=k===null,Y="em";
if(!!c){c=parseFloat(c)*(c.indexOf(Y)>-1?(P||V()):1)
}if(!!k){k=parseFloat(k)*(k.indexOf(Y)>-1?(P||V()):1)
}if(!l.hasquery||(!a||!m)&&(a||h>=c)&&(m||h<=k)){if(!d[l.media]){d[l.media]=[]
}d[l.media].push(K[l.rules])
}}for(var e in Q){if(Q[e]&&Q[e].parentNode===F){F.removeChild(Q[e])
}}for(var e in d){var n=W.createElement("style"),f=d[e].join("\n");
n.type="text/css";
n.media=e;
F.insertBefore(n,g.nextSibling);
if(n.styleSheet){n.styleSheet.cssText=f
}else{n.appendChild(W.createTextNode(f))
}Q.push(n)
}},N=function(X,Z){var Y=C();
if(!Y){return 
}Y.open("GET",X,true);
Y.onreadystatechange=function(){if(Y.readyState!=4||Y.status!=200&&Y.status!=304){return 
}Z(Y.responseText)
};
if(Y.readyState==4){return 
}Y.send(null)
},C=(function(){var X=false;
try{X=new XMLHttpRequest()
}catch(Y){X=new ActiveXObject("Microsoft.XMLHTTP")
}return function(){return X
}
})();
A();
respond.update=A;
function T(){J(true)
}if(E.addEventListener){E.addEventListener("resize",T,false)
}else{if(E.attachEvent){E.attachEvent("onresize",T)
}}})(this);