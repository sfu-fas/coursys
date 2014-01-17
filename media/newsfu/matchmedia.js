window.matchMedia||(window.matchMedia=function(H){var A=H.document,L=A.documentElement,E=[],J=0,G="",B={},I=/\s*(only|not)?\s*(screen|print|[a-z\-]+)\s*(and)?\s*/i,D=/^\s*\(\s*(-[a-z]+-)?(min-|max-)?([a-z\-]+)\s*(:?\s*([0-9]+(\.[0-9]+)?|portrait|landscape)(px|em|dppx|dpcm|rem|%|in|cm|mm|ex|pt|pc|\/([0-9]+(\.[0-9]+)?))?)?\s*\)\s*$/,C=0,F=function(X){var a=(X.indexOf(",")!==-1&&X.split(","))||[X],i=a.length-1,V=i,e=null,T=null,g="",c=0,Q=false,R="",O="",Y=null,h=0,U=0,P=null,f="",S="",b="",d="",W="",Z=false;
if(X===""){return true
}do{e=a[V-i];
Q=false;
T=e.match(I);
if(T){g=T[0];
c=T.index
}if(!T||((e.substring(0,c).indexOf("(")===-1)&&(c||(!T[3]&&g!==T.input)))){Z=false;
continue
}O=e;
Q=T[1]==="not";
if(!c){R=T[2];
O=e.substring(g.length)
}Z=R===G||R==="all"||R==="";
Y=(O.indexOf(" and ")!==-1&&O.split(" and "))||[O];
h=Y.length-1;
U=h;
if(Z&&h>=0&&O!==""){do{P=Y[h].match(D);
if(!P||!B[P[3]]){Z=false;
break
}f=P[2];
S=P[5];
d=S;
b=P[7];
W=B[P[3]];
if(b){if(b==="px"){d=Number(S)
}else{if(b==="em"||b==="rem"){d=16*S
}else{if(P[8]){d=(S/P[8]).toFixed(2)
}else{if(b==="dppx"){d=S*96
}else{if(b==="dpcm"){d=S*0.3937
}else{d=Number(S)
}}}}}}if(f==="min-"&&d){Z=W>=d
}else{if(f==="max-"&&d){Z=W<=d
}else{if(d){Z=W===d
}else{Z=!!W
}}}if(!Z){break
}}while(h--)
}if(Z){break
}}while(i--);
return Q?!Z:Z
},N=function(){var P=H.innerWidth||L.clientWidth,R=H.innerHeight||L.clientHeight,Q=H.screen.width,S=H.screen.height,T=H.screen.colorDepth,O=H.devicePixelRatio;
B.width=P;
B.height=R;
B["aspect-ratio"]=(P/R).toFixed(2);
B["device-width"]=Q;
B["device-height"]=S;
B["device-aspect-ratio"]=(Q/S).toFixed(2);
B.color=T;
B["color-index"]=Math.pow(2,T);
B.orientation=(R>=P?"portrait":"landscape");
B.resolution=(O&&O*96)||H.screen.deviceXDPI||96;
B["device-pixel-ratio"]=O||1
},M=function(){clearTimeout(C);
C=setTimeout(function(){var S=null,T=J-1,R=T,P=false;
if(T>=0){N();
do{S=E[R-T];
if(S){P=F(S.mql.media);
if((P&&!S.mql.matches)||(!P&&S.mql.matches)){S.mql.matches=P;
if(S.listeners){for(var Q=0,O=S.listeners.length;
Q<O;
Q++){if(S.listeners[Q]){S.listeners[Q].call(H,S.mql)
}}}}}}while(T--)
}},10)
},K=function(){var W=A.getElementsByTagName("head")[0],P=A.createElement("style"),Q=null,S=["screen","print","speech","projection","handheld","tv","braille","embossed","tty"],U=0,O=S.length,R="#mediamatchjs { position: relative; z-index: 0; }",V="",T=H.addEventListener||(V="on")&&H.attachEvent;
P.type="text/css";
P.id="mediamatchjs";
W.appendChild(P);
Q=(H.getComputedStyle&&H.getComputedStyle(P))||P.currentStyle;
for(;
U<O;
U++){R+="@media "+S[U]+" { #mediamatchjs { z-index: "+U+" } }"
}if(P.styleSheet){P.styleSheet.cssText=R
}else{P.textContent=R
}G=S[(Q.zIndex*1)||0];
W.removeChild(P);
N();
T(V+"resize",M);
T(V+"orientationchange",M)
};
K();
return function(R){var S=J,O={matches:false,media:R,addListener:function P(T){E[S].listeners||(E[S].listeners=[]);
T&&E[S].listeners.push(T)
},removeListener:function Q(W){var V=E[S],U=0,T=0;
if(!V){return 
}T=V.listeners.length;
for(;
U<T;
U++){if(V.listeners[U]===W){V.listeners.splice(U,1)
}}}};
if(R===""){O.matches=true;
return O
}O.matches=F(R);
J=E.push({mql:O,listeners:null});
return O
}
}(window));