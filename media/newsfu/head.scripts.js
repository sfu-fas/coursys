/*
 * hoverIntent r7 // 2013.03.11 // jQuery 1.9.1+
 * http://cherne.net/brian/resources/jquery.hoverIntent.html
 *
 * You may use hoverIntent under the terms of the MIT license. Basically that
 * means you are free to use hoverIntent as long as this header is left intact.
 * Copyright 2007, 2013 Brian Cherne
 */
(function(A){A.fn.hoverIntent=function(M,D,H){var J={interval:100,sensitivity:7,timeout:0};
if(typeof M==="object"){J=A.extend(J,M)
}else{if(A.isFunction(D)){J=A.extend(J,{over:M,out:D,selector:H})
}else{J=A.extend(J,{over:M,out:M,selector:D})
}}var L,K,G,F;
var E=function(N){L=N.pageX;
K=N.pageY
};
var C=function(O,N){N.hoverIntent_t=clearTimeout(N.hoverIntent_t);
if((Math.abs(G-L)+Math.abs(F-K))<J.sensitivity){A(N).off("mousemove.hoverIntent",E);
N.hoverIntent_s=1;
return J.over.apply(N,[O])
}else{G=L;
F=K;
N.hoverIntent_t=setTimeout(function(){C(O,N)
},J.interval)
}};
var I=function(O,N){N.hoverIntent_t=clearTimeout(N.hoverIntent_t);
N.hoverIntent_s=0;
return J.out.apply(N,[O])
};
var B=function(P){var O=jQuery.extend({},P);
var N=this;
if(N.hoverIntent_t){N.hoverIntent_t=clearTimeout(N.hoverIntent_t)
}if(P.type=="mouseenter"){G=O.pageX;
F=O.pageY;
A(N).on("mousemove.hoverIntent",E);
if(N.hoverIntent_s!=1){N.hoverIntent_t=setTimeout(function(){C(O,N)
},J.interval)
}}else{A(N).off("mousemove.hoverIntent",E);
if(N.hoverIntent_s==1){N.hoverIntent_t=setTimeout(function(){I(O,N)
},J.timeout)
}}};
return this.on({"mouseenter.hoverIntent":B,"mouseleave.hoverIntent":B},J.selector)
}
})(jQuery);
/*
 * fancyBox - jQuery Plugin
 * version: 2.0.6 (16/04/2012)
 * @requires jQuery v1.6 or later
 *
 * Examples at http://fancyapps.com/fancybox/
 * License: www.fancyapps.com/fancybox/#license
 *
 * Copyright 2012 Janis Skarnelis - janis@fancyapps.com
 *
 */
(function(K,M,I,E){var C=I(K),A=I(M),N=I.fancybox=function(){N.open.apply(this,arguments)
},O=false,J=null,G=M.createTouch!==E,B=function(D){return I.type(D)==="string"
},L=function(D){return B(D)&&D.indexOf("%")>0
},H=function(D,F){if(F&&L(D)){D=N.getViewport()[F]/100*parseInt(D,10)
}return Math.round(D)+"px"
};
I.extend(N,{version:"2.0.5",defaults:{padding:15,margin:20,width:800,height:600,minWidth:100,minHeight:100,maxWidth:9999,maxHeight:9999,autoSize:true,autoResize:!G,autoCenter:!G,fitToView:true,aspectRatio:false,topRatio:0.5,fixed:false,scrolling:"auto",wrapCSS:"",arrows:true,closeBtn:true,closeClick:false,nextClick:false,mouseWheel:true,autoPlay:false,playSpeed:3000,preload:3,modal:false,loop:true,ajax:{dataType:"html",headers:{"X-fancyBox":true}},keys:{next:[13,32,34,39,40],prev:[8,33,37,38],close:[27]},index:0,type:null,href:null,content:null,title:null,tpl:{wrap:'<div class="fancybox-wrap"><div class="fancybox-skin"><div class="fancybox-outer"><div class="fancybox-inner"></div></div></div></div>',image:'<img class="fancybox-image" src="{href}" alt="" />',iframe:'<iframe class="fancybox-iframe" name="fancybox-frame{rnd}" frameborder="0" hspace="0"'+(I.browser.msie?' allowtransparency="true"':"")+"></iframe>",swf:'<object classid="clsid:D27CDB6E-AE6D-11cf-96B8-444553540000" width="100%" height="100%"><param name="wmode" value="transparent" /><param name="allowfullscreen" value="true" /><param name="allowscriptaccess" value="always" /><param name="movie" value="{href}" /><embed src="{href}" type="application/x-shockwave-flash" allowfullscreen="true" allowscriptaccess="always" width="100%" height="100%" wmode="transparent"></embed></object>',error:'<p class="fancybox-error">The requested content cannot be loaded.<br/>Please try again later.</p>',closeBtn:'<div title="Close" class="fancybox-item fancybox-close"></div>',next:'<a title="Next" class="fancybox-nav fancybox-next"><span></span></a>',prev:'<a title="Previous" class="fancybox-nav fancybox-prev"><span></span></a>'},openEffect:"fade",openSpeed:300,openEasing:"swing",openOpacity:true,openMethod:"zoomIn",closeEffect:"fade",closeSpeed:300,closeEasing:"swing",closeOpacity:true,closeMethod:"zoomOut",nextEffect:"elastic",nextSpeed:300,nextEasing:"swing",nextMethod:"changeIn",prevEffect:"elastic",prevSpeed:300,prevEasing:"swing",prevMethod:"changeOut",helpers:{overlay:{speedIn:0,speedOut:300,opacity:0.8,css:{cursor:"pointer"},closeClick:true},title:{type:"float"}},onCancel:I.noop,beforeLoad:I.noop,afterLoad:I.noop,beforeShow:I.noop,afterShow:I.noop,beforeClose:I.noop,afterClose:I.noop},group:{},opts:{},coming:null,current:null,isOpen:false,isOpened:false,wrap:null,skin:null,outer:null,inner:null,player:{timer:null,isActive:false},ajaxLoad:null,imgPreload:null,transitions:{},helpers:{},open:function(F,D){N.close(true);
if(F&&!I.isArray(F)){F=F instanceof I?I(F).get():[F]
}N.isActive=true;
N.opts=I.extend(true,{},N.defaults,D);
if(I.isPlainObject(D)&&D.keys!==E){N.opts.keys=D.keys?I.extend({},N.defaults.keys,D.keys):false
}N.group=F;
N._start(N.opts.index||0)
},cancel:function(){if(N.coming&&false===N.trigger("onCancel")){return 
}N.coming=null;
N.hideLoading();
if(N.ajaxLoad){N.ajaxLoad.abort()
}N.ajaxLoad=null;
if(N.imgPreload){N.imgPreload.onload=N.imgPreload.onabort=N.imgPreload.onerror=null
}},close:function(D){N.cancel();
if(!N.current||false===N.trigger("beforeClose")){return 
}N.unbindEvents();
if(!N.isOpen||(D&&D[0]===true)){I(".fancybox-wrap").stop().trigger("onReset").remove();
N._afterZoomOut()
}else{N.isOpen=N.isOpened=false;
I(".fancybox-item, .fancybox-nav").remove();
N.wrap.stop(true).removeClass("fancybox-opened");
N.inner.css("overflow","hidden");
N.transitions[N.current.closeMethod]()
}},play:function(F){var D=function(){clearTimeout(N.player.timer)
},R=function(){D();
if(N.current&&N.player.isActive){N.player.timer=setTimeout(N.next,N.current.playSpeed)
}},P=function(){D();
I("body").unbind(".player");
N.player.isActive=false;
N.trigger("onPlayEnd")
},Q=function(){if(N.current&&(N.current.loop||N.current.index<N.group.length-1)){N.player.isActive=true;
I("body").bind({"afterShow.player onUpdate.player":R,"onCancel.player beforeClose.player":P,"beforeLoad.player":D});
R();
N.trigger("onPlayStart")
}};
if(N.player.isActive||(F&&F[0]===false)){P()
}else{Q()
}},next:function(){if(N.current){N.jumpto(N.current.index+1)
}},prev:function(){if(N.current){N.jumpto(N.current.index-1)
}},jumpto:function(D){if(!N.current){return 
}D=parseInt(D,10);
if(N.group.length>1&&N.current.loop){if(D>=N.group.length){D=0
}else{if(D<0){D=N.group.length-1
}}}if(N.group[D]!==E){N.cancel();
N._start(D)
}},reposition:function(F,D){var P;
if(N.isOpen){P=N._getPosition(D);
if(F&&F.type==="scroll"){delete P.position;
N.wrap.stop(true,true).animate(P,200)
}else{N.wrap.css(P)
}}},update:function(D){if(!N.isOpen){return 
}if(!O){J=setTimeout(function(){var P=N.current,F=!D||(D&&D.type==="orientationchange");
if(O){O=false;
if(!P){return 
}if((!D||D.type!=="scroll")||F){if(P.autoSize&&P.type!=="iframe"){N.inner.height("auto");
P.height=N.inner.height()
}if(P.autoResize||F){N._setDimension()
}if(P.canGrow&&P.type!=="iframe"){N.inner.height("auto")
}}if(P.autoCenter||F){N.reposition(D)
}N.trigger("onUpdate")
}},200)
}O=true
},toggle:function(){if(N.isOpen){N.current.fitToView=!N.current.fitToView;
N.update()
}},hideLoading:function(){A.unbind("keypress.fb");
I("#fancybox-loading").remove()
},showLoading:function(){N.hideLoading();
A.bind("keypress.fb",function(D){if(D.keyCode===27){D.preventDefault();
N.cancel()
}});
I('<div id="fancybox-loading"><div></div></div>').click(N.cancel).appendTo("body")
},getViewport:function(){return{x:C.scrollLeft(),y:C.scrollTop(),w:G&&K.innerWidth?K.innerWidth:C.width(),h:G&&K.innerHeight?K.innerHeight:C.height()}
},unbindEvents:function(){if(N.wrap){N.wrap.unbind(".fb")
}A.unbind(".fb");
C.unbind(".fb")
},bindEvents:function(){var F=N.current,D=F.keys;
if(!F){return 
}C.bind("resize.fb orientationchange.fb"+(F.autoCenter&&!F.fixed?" scroll.fb":""),N.update);
if(D){A.bind("keydown.fb",function(R){var P,Q=R.target||R.srcElement;
if(!R.ctrlKey&&!R.altKey&&!R.shiftKey&&!R.metaKey&&!(Q&&(Q.type||I(Q).is("[contenteditable]")))){P=R.keyCode;
if(I.inArray(P,D.close)>-1){N.close();
R.preventDefault()
}else{if(I.inArray(P,D.next)>-1){N.next();
R.preventDefault()
}else{if(I.inArray(P,D.prev)>-1){N.prev();
R.preventDefault()
}}}}})
}if(I.fn.mousewheel&&F.mouseWheel&&N.group.length>1){N.wrap.bind("mousewheel.fb",function(Q,R){var P=Q.target||null;
if(R!==0&&(!P||P.clientHeight===0||(P.scrollHeight===P.clientHeight&&P.scrollWidth===P.clientWidth))){Q.preventDefault();
N[R>0?"prev":"next"]()
}})
}},trigger:function(F,Q){var D,P=Q||N[I.inArray(F,["onCancel","beforeLoad","afterLoad"])>-1?"coming":"current"];
if(!P){return 
}if(I.isFunction(P[F])){D=P[F].apply(P,Array.prototype.slice.call(arguments,1))
}if(D===false){return false
}if(P.helpers){I.each(P.helpers,function(S,R){if(R&&I.isPlainObject(N.helpers[S])&&I.isFunction(N.helpers[S][F])){N.helpers[S][F](R,P)
}})
}I.event.trigger(F+".fb")
},isImage:function(D){return B(D)&&D.match(/\.(jpe?g|gif|png|bmp)((\?|#).*)?$/i)
},isSWF:function(D){return B(D)&&D.match(/\.(swf)((\?|#).*)?$/i)
},_start:function(F){var R={},Q=N.group[F]||null,P,D,S,T,U;
if(Q&&(Q.nodeType||Q instanceof I)){P=true;
if(I.metadata){R=I(Q).metadata()
}}R=I.extend(true,{},N.opts,{index:F,element:Q},(I.isPlainObject(Q)?Q:R));
I.each(["href","title","content","type"],function(W,V){R[V]=N.opts[V]||(P&&I(Q).attr(V))||R[V]||null
});
if(typeof R.margin==="number"){R.margin=[R.margin,R.margin,R.margin,R.margin]
}if(R.modal){I.extend(true,R,{closeBtn:false,closeClick:false,nextClick:false,arrows:false,mouseWheel:false,keys:null,helpers:{overlay:{css:{cursor:"auto"},closeClick:false}}})
}N.coming=R;
if(false===N.trigger("beforeLoad")){N.coming=null;
return 
}S=R.type;
D=R.href||Q;
if(!S){if(P){S=I(Q).data("fancybox-type");
if(!S){T=Q.className.match(/fancybox\.(\w+)/);
S=T?T[1]:null
}}if(!S&&B(D)){if(N.isImage(D)){S="image"
}else{if(N.isSWF(D)){S="swf"
}else{if(D.match(/^#/)){S="inline"
}}}}if(!S){S=P?"inline":"html"
}R.type=S
}if(S==="inline"||S==="html"){if(!R.content){if(S==="inline"){R.content=I(B(D)?D.replace(/.*(?=#[^\s]+$)/,""):D)
}else{R.content=Q
}}if(!R.content||!R.content.length){S=null
}}else{if(!D){S=null
}}if(S==="ajax"&&B(D)){U=D.split(/\s+/,2);
D=U.shift();
R.selector=U.shift()
}R.href=D;
R.group=N.group;
R.isDom=P;
switch(S){case"image":N._loadImage();
break;
case"ajax":N._loadAjax();
break;
case"inline":case"iframe":case"swf":case"html":N._afterLoad();
break;
default:N._error("type")
}},_error:function(D){N.hideLoading();
I.extend(N.coming,{type:"html",autoSize:true,minWidth:0,minHeight:0,padding:15,hasError:D,content:N.coming.tpl.error});
N._afterLoad()
},_loadImage:function(){var D=N.imgPreload=new Image();
D.onload=function(){this.onload=this.onerror=null;
N.coming.width=this.width;
N.coming.height=this.height;
N._afterLoad()
};
D.onerror=function(){this.onload=this.onerror=null;
N._error("image")
};
D.src=N.coming.href;
if(D.complete===E||!D.complete){N.showLoading()
}},_loadAjax:function(){N.showLoading();
N.ajaxLoad=I.ajax(I.extend({},N.coming.ajax,{url:N.coming.href,error:function(D,F){if(N.coming&&F!=="abort"){N._error("ajax",D)
}else{N.hideLoading()
}},success:function(D,F){if(F==="success"){N.coming.content=D;
N._afterLoad()
}}}))
},_preloadImages:function(){var T=N.group,S=N.current,D=T.length,R,F,Q,P=Math.min(S.preload,D-1);
if(!S.preload||T.length<2){return 
}for(Q=1;
Q<=P;
Q+=1){R=T[(S.index+Q)%D];
F=R.href||I(R).attr("href")||R;
if(R.type==="image"||N.isImage(F)){new Image().src=F
}}},_afterLoad:function(){N.hideLoading();
if(!N.coming||false===N.trigger("afterLoad",N.current)){N.coming=false;
return 
}if(N.isOpened){I(".fancybox-item, .fancybox-nav").remove();
N.wrap.stop(true).removeClass("fancybox-opened");
N.inner.css("overflow","hidden");
N.transitions[N.current.prevMethod]()
}else{I(".fancybox-wrap").stop().trigger("onReset").remove();
N.trigger("afterClose")
}N.unbindEvents();
N.isOpen=false;
N.current=N.coming;
N.wrap=I(N.current.tpl.wrap).addClass("fancybox-"+(G?"mobile":"desktop")+" fancybox-type-"+N.current.type+" fancybox-tmp "+N.current.wrapCSS).appendTo("body");
N.skin=I(".fancybox-skin",N.wrap).css("padding",H(N.current.padding));
N.outer=I(".fancybox-outer",N.wrap);
N.inner=I(".fancybox-inner",N.wrap);
N._setContent()
},_setContent:function(){var U=N.current,R=U.content,F=U.type,D=U.minWidth,T=U.minHeight,Q=U.maxWidth,P=U.maxHeight,S;
switch(F){case"inline":case"ajax":case"html":if(U.selector){R=I("<div>").html(R).find(U.selector)
}else{if(R instanceof I){if(R.parent().hasClass("fancybox-inner")){R.parents(".fancybox-wrap").unbind("onReset")
}R=R.show().detach();
I(N.wrap).bind("onReset",function(){R.appendTo("body").hide()
})
}}if(U.autoSize){S=I('<div class="fancybox-wrap '+N.current.wrapCSS+' fancybox-tmp"></div>').appendTo("body").css({minWidth:H(D,"w"),minHeight:H(T,"h"),maxWidth:H(Q,"w"),maxHeight:H(P,"h")}).append(R);
U.width=S.width();
U.height=S.height();
S.width(N.current.width);
if(S.height()>U.height){S.width(U.width+1);
U.width=S.width();
U.height=S.height()
}R=S.contents().detach();
S.remove()
}break;
case"image":R=U.tpl.image.replace("{href}",U.href);
U.aspectRatio=true;
break;
case"swf":R=U.tpl.swf.replace(/\{width\}/g,U.width).replace(/\{height\}/g,U.height).replace(/\{href\}/g,U.href);
break;
case"iframe":R=I(U.tpl.iframe.replace("{rnd}",new Date().getTime())).attr("scrolling",U.scrolling).attr("src",U.href);
U.scrolling=G?"scroll":"auto";
break
}if(F==="image"||F==="swf"){U.autoSize=false;
U.scrolling="visible"
}if(F==="iframe"&&U.autoSize){N.showLoading();
N._setDimension();
N.inner.css("overflow",U.scrolling);
R.bind({onCancel:function(){I(this).unbind();
N._afterZoomOut()
},load:function(){N.hideLoading();
try{if(this.contentWindow.document.location){N.current.height=I(this).contents().find("body").height()
}}catch(V){N.current.autoSize=false
}N[N.isOpen?"_afterZoomIn":"_beforeShow"]()
}}).appendTo(N.inner)
}else{N.inner.append(R);
N._beforeShow()
}},_beforeShow:function(){N.coming=null;
N.trigger("beforeShow");
N._setDimension();
N.wrap.hide().removeClass("fancybox-tmp");
N.bindEvents();
N._preloadImages();
N.transitions[N.isOpened?N.current.nextMethod:N.current.openMethod]()
},_setDimension:function(){var P=N.wrap,a=N.inner,T=N.current,U=N.getViewport(),R=T.margin,D=T.padding*2,Q=T.width,Z=T.height,X=T.maxWidth+D,W=T.maxHeight+D,F=T.minWidth+D,Y=T.minHeight+D,V,S;
U.w-=(R[1]+R[3]);
U.h-=(R[0]+R[2]);
if(L(Q)){Q=(((U.w-D)*parseFloat(Q))/100)
}if(L(Z)){Z=(((U.h-D)*parseFloat(Z))/100)
}V=Q/Z;
Q+=D;
Z+=D;
if(T.fitToView){X=Math.min(U.w,X);
W=Math.min(U.h,W)
}if(T.aspectRatio){if(Q>X){Q=X;
Z=((Q-D)/V)+D
}if(Z>W){Z=W;
Q=((Z-D)*V)+D
}if(Q<F){Q=F;
Z=((Q-D)/V)+D
}if(Z<Y){Z=Y;
Q=((Z-D)*V)+D
}}else{Q=Math.max(F,Math.min(Q,X));
Z=Math.max(Y,Math.min(Z,W))
}Q=Math.round(Q);
Z=Math.round(Z);
I(P.add(a)).width("auto").height("auto");
a.width(Q-D).height(Z-D);
P.width(Q);
S=P.height();
if(Q>X||S>W){while((Q>X||S>W)&&Q>F&&S>Y){Z=Z-10;
if(T.aspectRatio){Q=Math.round(((Z-D)*V)+D);
if(Q<F){Q=F;
Z=((Q-D)/V)+D
}}else{Q=Q-10
}a.width(Q-D).height(Z-D);
P.width(Q);
S=P.height()
}}T.dim={width:H(Q),height:H(S)};
T.canGrow=T.autoSize&&Z>Y&&Z<W;
T.canShrink=false;
T.canExpand=false;
if((Q-D)<T.width||(Z-D)<T.height){T.canExpand=true
}else{if((Q>U.w||S>U.h)&&Q>F&&Z>Y){T.canShrink=true
}}N.innerSpace=S-D-a.height()
},_getPosition:function(P){var T=N.current,F=N.getViewport(),R=T.margin,Q=N.wrap.width()+R[1]+R[3],D=N.wrap.height()+R[0]+R[2],S={position:"absolute",top:R[0]+F.y,left:R[3]+F.x};
if(T.autoCenter&&T.fixed&&!P&&D<=F.h&&Q<=F.w){S={position:"fixed",top:R[0],left:R[3]}
}S.top=H(Math.max(S.top,S.top+((F.h-D)*T.topRatio)));
S.left=H(Math.max(S.left,S.left+((F.w-Q)*0.5)));
return S
},_afterZoomIn:function(){var F=N.current,D=F?F.scrolling:"no";
if(!F){return 
}N.isOpen=N.isOpened=true;
N.wrap.addClass("fancybox-opened");
N.inner.css("overflow",D==="yes"?"scroll":(D==="no"?"hidden":D));
N.trigger("afterShow");
N.update();
if(F.closeClick||F.nextClick){N.inner.css("cursor","pointer").bind("click.fb",function(P){if(!I(P.target).is("a")&&!I(P.target).parent().is("a")){N[F.closeClick?"close":"next"]()
}})
}if(F.closeBtn){I(F.tpl.closeBtn).appendTo(N.skin).bind("click.fb",N.close)
}if(F.arrows&&N.group.length>1){if(F.loop||F.index>0){I(F.tpl.prev).appendTo(N.outer).bind("click.fb",N.prev)
}if(F.loop||F.index<N.group.length-1){I(F.tpl.next).appendTo(N.outer).bind("click.fb",N.next)
}}if(N.opts.autoPlay&&!N.player.isActive){N.opts.autoPlay=false;
N.play()
}},_afterZoomOut:function(){var D=N.current;
N.wrap.trigger("onReset").remove();
I.extend(N,{group:{},opts:{},current:null,isActive:false,isOpened:false,isOpen:false,wrap:null,skin:null,outer:null,inner:null});
N.trigger("afterClose",D)
}});
N.transitions={getOrigPosition:function(){var S=N.current,P=S.element,R=S.padding,U=I(S.orig),T={},Q=50,F=50,D;
if(!U.length&&S.isDom&&I(P).is(":visible")){U=I(P).find("img:first");
if(!U.length){U=I(P)
}}if(U.length){T=U.offset();
if(U.is("img")){Q=U.outerWidth();
F=U.outerHeight()
}}else{D=N.getViewport();
T.top=D.y+(D.h-F)*0.5;
T.left=D.x+(D.w-Q)*0.5
}T={top:H(T.top-R),left:H(T.left-R),width:H(Q+R*2),height:H(F+R*2)};
return T
},step:function(D,P){var R=P.prop,Q,F;
if(R==="width"||R==="height"){Q=Math.ceil(D-(N.current.padding*2));
if(R==="height"){F=(D-P.start)/(P.end-P.start);
if(P.start>P.end){F=1-F
}Q-=N.innerSpace*F
}N.inner[R](Q)
}},zoomIn:function(){var Q=N.wrap,T=N.current,P=T.openEffect,S=P==="elastic",R=T.dim,F=I.extend({},R,N._getPosition(S)),D=I.extend({opacity:1},F);
delete D.position;
if(S){F=this.getOrigPosition();
if(T.openOpacity){F.opacity=0
}N.outer.add(N.inner).width("auto").height("auto")
}else{if(P==="fade"){F.opacity=0
}}Q.css(F).show().animate(D,{duration:P==="none"?0:T.openSpeed,easing:T.openEasing,step:S?this.step:null,complete:N._afterZoomIn})
},zoomOut:function(){var P=N.wrap,R=N.current,F=R.openEffect,Q=F==="elastic",D={opacity:0};
if(Q){if(P.css("position")==="fixed"){P.css(N._getPosition(true))
}D=this.getOrigPosition();
if(R.closeOpacity){D.opacity=0
}}P.animate(D,{duration:F==="none"?0:R.closeSpeed,easing:R.closeEasing,step:Q?this.step:null,complete:N._afterZoomOut})
},changeIn:function(){var Q=N.wrap,S=N.current,P=S.nextEffect,R=P==="elastic",F=N._getPosition(R),D={opacity:1};
F.opacity=0;
if(R){F.top=H(parseInt(F.top,10)-200);
D.top="+=200px"
}Q.css(F).show().animate(D,{duration:P==="none"?0:S.nextSpeed,easing:S.nextEasing,complete:N._afterZoomIn})
},changeOut:function(){var P=N.wrap,R=N.current,F=R.prevEffect,D={opacity:0},Q=function(){I(this).trigger("onReset").remove()
};
P.removeClass("fancybox-opened");
if(F==="elastic"){D.top="+=200px"
}P.animate(D,{duration:F==="none"?0:R.prevSpeed,easing:R.prevEasing,complete:Q})
}};
N.helpers.overlay={overlay:null,update:function(){var P,D,F;
this.overlay.width("100%").height("100%");
if(I.browser.msie||G){D=Math.max(M.documentElement.scrollWidth,M.body.scrollWidth);
F=Math.max(M.documentElement.offsetWidth,M.body.offsetWidth);
P=D<F?C.width():D
}else{P=A.width()
}this.overlay.width(P).height(A.height())
},beforeShow:function(D){if(this.overlay){return 
}D=I.extend(true,{},N.defaults.helpers.overlay,D);
this.overlay=I('<div id="fancybox-overlay"></div>').css(D.css).appendTo("body");
if(D.closeClick){this.overlay.bind("click.fb",N.close)
}if(N.current.fixed&&!G){this.overlay.addClass("overlay-fixed")
}else{this.update();
this.onUpdate=function(){this.update()
}
}this.overlay.fadeTo(D.speedIn,D.opacity)
},afterClose:function(D){if(this.overlay){this.overlay.fadeOut(D.speedOut||0,function(){I(this).remove()
})
}this.overlay=null
}};
N.helpers.title={beforeShow:function(D){var P,F=N.current.title;
if(F){P=I('<div class="fancybox-title fancybox-title-'+D.type+'-wrap">'+F+"</div>").appendTo("body");
if(D.type==="float"){P.width(P.width());
P.wrapInner('<span class="child"></span>');
N.current.margin[2]+=Math.abs(parseInt(P.css("margin-bottom"),10))
}P.appendTo(D.type==="over"?N.inner:(D.type==="outside"?N.wrap:N.skin))
}}};
I.fn.fancybox=function(P){var Q=I(this),D=this.selector||"",F,R=function(V){var U=this,S=F,T,W;
if(!(V.ctrlKey||V.altKey||V.shiftKey||V.metaKey)&&!I(U).is(".fancybox-wrap")){V.preventDefault();
T=P.groupAttr||"data-fancybox-group";
W=I(U).attr(T);
if(!W){T="rel";
W=U[T]
}if(W&&W!==""&&W!=="nofollow"){U=D.length?I(D):Q;
U=U.filter("["+T+'="'+W+'"]');
S=U.index(this)
}P.index=S;
N.open(U,P)
}};
P=P||{};
F=P.index||0;
if(D){A.undelegate(D,"click.fb-start").delegate(D,"click.fb-start",R)
}else{Q.unbind("click.fb-start").bind("click.fb-start",R)
}return this
};
I(M).ready(function(){N.defaults.fixed=I.support.fixedPosition||(!(I.browser.msie&&I.browser.version<=6)&&!G)
})
}(window,document,jQuery));
(function(B){var A=B.fancybox;
A.helpers.buttons={tpl:'<div id="fancybox-buttons"><ul><li><a class="btnPrev" title="Previous" href="javascript:jQuery.fancybox.prev();">Previous</a></li><li><a class="btnPlay" title="Slideshow" href="javascript:jQuery.fancybox.play();;">Play</a></li><li><a class="btnNext" title="Next" href="javascript:jQuery.fancybox.next();">Next</a></li><li><a class="btnToggle" title="Toggle size" href="javascript:jQuery.fancybox.toggle();">Toggle</a></li><li><a class="btnClose" title="Close" href="javascript:jQuery.fancybox.close();">Close</a></li></ul></div>',list:null,buttons:{},update:function(){var C=this.buttons.toggle.removeClass("btnDisabled btnToggleOn");
if(A.current.canShrink){C.addClass("btnToggleOn")
}else{if(!A.current.canExpand){C.addClass("btnDisabled")
}}},beforeShow:function(){A.current.margin[0]+=30
},onPlayStart:function(){if(this.list){this.buttons.play.text("Pause").addClass("btnPlayOn")
}},onPlayEnd:function(){if(this.list){this.buttons.play.text("Play").removeClass("btnPlayOn")
}},afterShow:function(){if(!this.list){this.list=B(this.tpl).appendTo("body");
this.buttons={prev:this.list.find(".btnPrev"),next:this.list.find(".btnNext"),play:this.list.find(".btnPlay"),toggle:this.list.find(".btnToggle")}
}if(A.current.index>0||A.current.loop){this.buttons.prev.removeClass("btnDisabled")
}else{this.buttons.prev.addClass("btnDisabled")
}if(A.current.loop||A.current.index<A.group.length-1){this.buttons.next.removeClass("btnDisabled");
this.buttons.play.removeClass("btnDisabled")
}else{this.buttons.next.addClass("btnDisabled");
this.buttons.play.addClass("btnDisabled")
}this.update()
},onUpdate:function(){this.update()
},beforeClose:function(C){if(this.list){this.list.remove()
}this.list=null;
this.buttons={}
}}
}(jQuery));
(function(B){var A=B.fancybox;
A.helpers.thumbs={wrap:null,list:null,width:0,source:function(D){var C=B(D).find("img");
return C.length?C.attr("src"):D.href
},init:function(D){var C=this,E;
E="";
for(var F=0;
F<A.group.length;
F++){E+='<li><a style="width:'+D.width+"px;height:"+D.height+'px;" href="javascript:jQuery.fancybox.jumpto('+F+');"></a></li>'
}this.wrap=B('<div id="fancybox-thumbs"></div>').appendTo("body");
this.list=B("<ul>"+E+"</ul>").appendTo(this.wrap);
B.each(A.group,function(G){B("<img />").load(function(){var L=this.width,H=this.height,K,I,J;
if(!C.list||!L||!H){return 
}K=L/D.width;
I=H/D.height;
J=C.list.children().eq(G).find("a");
if(K>=1&&I>=1){if(K>I){L=Math.floor(L/I);
H=D.height
}else{L=D.width;
H=Math.floor(H/K)
}}B(this).css({width:L,height:H,top:Math.floor(D.height/2-H/2),left:Math.floor(D.width/2-L/2)});
J.width(D.width).height(D.height);
B(this).hide().appendTo(J).fadeIn(300)
}).attr("src",D.source?D.source(this):C.source(this))
});
this.width=this.list.children().eq(0).outerWidth();
this.list.width(this.width*(A.group.length+1)).css("left",Math.floor(B(window).width()*0.5-(A.current.index*this.width+this.width*0.5)))
},update:function(C){if(this.list){this.list.stop(true).animate({left:Math.floor(B(window).width()*0.5-(A.current.index*this.width+this.width*0.5))},150)
}},beforeLoad:function(C){if(A.group.length<2){A.coming.helpers.thumbs=false;
return 
}A.coming.margin[2]=C.height+30
},afterShow:function(C){if(this.list){this.update(C)
}else{this.init(C)
}this.list.children().removeClass("active").eq(A.current.index).addClass("active")
},onUpdate:function(){this.update()
},beforeClose:function(){if(this.wrap){this.wrap.remove()
}this.wrap=null;
this.list=null;
this.width=0
}}
}(jQuery));
jQuery.easing.jswing=jQuery.easing.swing;
jQuery.extend(jQuery.easing,{def:"easeOutQuad",swing:function(B,C,A,E,D){return jQuery.easing[jQuery.easing.def](B,C,A,E,D)
},easeInQuad:function(B,C,A,E,D){return E*(C/=D)*C+A
},easeOutQuad:function(B,C,A,E,D){return -E*(C/=D)*(C-2)+A
},easeInOutQuad:function(B,C,A,E,D){if((C/=D/2)<1){return E/2*C*C+A
}return -E/2*((--C)*(C-2)-1)+A
},easeInCubic:function(B,C,A,E,D){return E*(C/=D)*C*C+A
},easeOutCubic:function(B,C,A,E,D){return E*((C=C/D-1)*C*C+1)+A
},easeInOutCubic:function(B,C,A,E,D){if((C/=D/2)<1){return E/2*C*C*C+A
}return E/2*((C-=2)*C*C+2)+A
},easeInQuart:function(B,C,A,E,D){return E*(C/=D)*C*C*C+A
},easeOutQuart:function(B,C,A,E,D){return -E*((C=C/D-1)*C*C*C-1)+A
},easeInOutQuart:function(B,C,A,E,D){if((C/=D/2)<1){return E/2*C*C*C*C+A
}return -E/2*((C-=2)*C*C*C-2)+A
},easeInQuint:function(B,C,A,E,D){return E*(C/=D)*C*C*C*C+A
},easeOutQuint:function(B,C,A,E,D){return E*((C=C/D-1)*C*C*C*C+1)+A
},easeInOutQuint:function(B,C,A,E,D){if((C/=D/2)<1){return E/2*C*C*C*C*C+A
}return E/2*((C-=2)*C*C*C*C+2)+A
},easeInSine:function(B,C,A,E,D){return -E*Math.cos(C/D*(Math.PI/2))+E+A
},easeOutSine:function(B,C,A,E,D){return E*Math.sin(C/D*(Math.PI/2))+A
},easeInOutSine:function(B,C,A,E,D){return -E/2*(Math.cos(Math.PI*C/D)-1)+A
},easeInExpo:function(B,C,A,E,D){return(C==0)?A:E*Math.pow(2,10*(C/D-1))+A
},easeOutExpo:function(B,C,A,E,D){return(C==D)?A+E:E*(-Math.pow(2,-10*C/D)+1)+A
},easeInOutExpo:function(B,C,A,E,D){if(C==0){return A
}if(C==D){return A+E
}if((C/=D/2)<1){return E/2*Math.pow(2,10*(C-1))+A
}return E/2*(-Math.pow(2,-10*--C)+2)+A
},easeInCirc:function(B,C,A,E,D){return -E*(Math.sqrt(1-(C/=D)*C)-1)+A
},easeOutCirc:function(B,C,A,E,D){return E*Math.sqrt(1-(C=C/D-1)*C)+A
},easeInOutCirc:function(B,C,A,E,D){if((C/=D/2)<1){return -E/2*(Math.sqrt(1-C*C)-1)+A
}return E/2*(Math.sqrt(1-(C-=2)*C)+1)+A
},easeInElastic:function(B,D,A,H,G){var E=1.70158;
var F=0;
var C=H;
if(D==0){return A
}if((D/=G)==1){return A+H
}if(!F){F=G*0.3
}if(C<Math.abs(H)){C=H;
var E=F/4
}else{var E=F/(2*Math.PI)*Math.asin(H/C)
}return -(C*Math.pow(2,10*(D-=1))*Math.sin((D*G-E)*(2*Math.PI)/F))+A
},easeOutElastic:function(B,D,A,H,G){var E=1.70158;
var F=0;
var C=H;
if(D==0){return A
}if((D/=G)==1){return A+H
}if(!F){F=G*0.3
}if(C<Math.abs(H)){C=H;
var E=F/4
}else{var E=F/(2*Math.PI)*Math.asin(H/C)
}return C*Math.pow(2,-10*D)*Math.sin((D*G-E)*(2*Math.PI)/F)+H+A
},easeInOutElastic:function(B,D,A,H,G){var E=1.70158;
var F=0;
var C=H;
if(D==0){return A
}if((D/=G/2)==2){return A+H
}if(!F){F=G*(0.3*1.5)
}if(C<Math.abs(H)){C=H;
var E=F/4
}else{var E=F/(2*Math.PI)*Math.asin(H/C)
}if(D<1){return -0.5*(C*Math.pow(2,10*(D-=1))*Math.sin((D*G-E)*(2*Math.PI)/F))+A
}return C*Math.pow(2,-10*(D-=1))*Math.sin((D*G-E)*(2*Math.PI)/F)*0.5+H+A
},easeInBack:function(B,C,A,F,E,D){if(D==undefined){D=1.70158
}return F*(C/=E)*C*((D+1)*C-D)+A
},easeOutBack:function(B,C,A,F,E,D){if(D==undefined){D=1.70158
}return F*((C=C/E-1)*C*((D+1)*C+D)+1)+A
},easeInOutBack:function(B,C,A,F,E,D){if(D==undefined){D=1.70158
}if((C/=E/2)<1){return F/2*(C*C*(((D*=(1.525))+1)*C-D))+A
}return F/2*((C-=2)*C*(((D*=(1.525))+1)*C+D)+2)+A
},easeInBounce:function(B,C,A,E,D){return E-jQuery.easing.easeOutBounce(B,D-C,0,E,D)+A
},easeOutBounce:function(B,C,A,E,D){if((C/=D)<(1/2.75)){return E*(7.5625*C*C)+A
}else{if(C<(2/2.75)){return E*(7.5625*(C-=(1.5/2.75))*C+0.75)+A
}else{if(C<(2.5/2.75)){return E*(7.5625*(C-=(2.25/2.75))*C+0.9375)+A
}else{return E*(7.5625*(C-=(2.625/2.75))*C+0.984375)+A
}}}},easeInOutBounce:function(B,C,A,E,D){if(C<D/2){return jQuery.easing.easeInBounce(B,C*2,0,E,D)*0.5+A
}return jQuery.easing.easeOutBounce(B,C*2-D,0,E,D)*0.5+E*0.5+A
}});
/* Copyright (c) 2011 Brandon Aaron (http://brandonaaron.net)
 * Licensed under the MIT License (LICENSE.txt).
 *
 * Thanks to: http://adomas.org/javascript-mouse-wheel/ for some pointers.
 * Thanks to: Mathias Bank(http://www.mathias-bank.de) for a scope bug fix.
 * Thanks to: Seamus Leahy for adding deltaX and deltaY
 *
 * Version: 3.0.6
 * 
 * Requires: 1.2.2+
 */
(function(D){var B=["DOMMouseScroll","mousewheel"];
if(D.event.fixHooks){for(var A=B.length;
A;
){D.event.fixHooks[B[--A]]=D.event.mouseHooks
}}D.event.special.mousewheel={setup:function(){if(this.addEventListener){for(var E=B.length;
E;
){this.addEventListener(B[--E],C,false)
}}else{this.onmousewheel=C
}},teardown:function(){if(this.removeEventListener){for(var E=B.length;
E;
){this.removeEventListener(B[--E],C,false)
}}else{this.onmousewheel=null
}}};
D.fn.extend({mousewheel:function(E){return E?this.bind("mousewheel",E):this.trigger("mousewheel")
},unmousewheel:function(E){return this.unbind("mousewheel",E)
}});
function C(J){var H=J||window.event,G=[].slice.call(arguments,1),K=0,I=true,F=0,E=0;
J=D.event.fix(H);
J.type="mousewheel";
if(H.wheelDelta){K=H.wheelDelta/120
}if(H.detail){K=-H.detail/3
}E=K;
if(H.axis!==undefined&&H.axis===H.HORIZONTAL_AXIS){E=0;
F=-1*K
}if(H.wheelDeltaY!==undefined){E=H.wheelDeltaY/120
}if(H.wheelDeltaX!==undefined){F=-1*H.wheelDeltaX/120
}G.unshift(J,K,F,E);
return(D.event.dispatch||D.event.handle).apply(this,G)
}})(jQuery);
window.Modernizr=(function(L,Q,G){var C="2.6.2",J={},Z=Q.documentElement,a="modernizr",W=Q.createElement(a),M=W.style,D=Q.createElement("input"),X=":)",T={}.toString,H={},B={},R={},V=[],S=V.slice,A,O=({}).hasOwnProperty,Y;
if(!I(O,"undefined")&&!I(O.call,"undefined")){Y=function(c,d){return O.call(c,d)
}
}else{Y=function(c,d){return((d in c)&&I(c.constructor.prototype[d],"undefined"))
}
}if(!Function.prototype.bind){Function.prototype.bind=function b(e){var f=this;
if(typeof f!="function"){throw new TypeError()
}var c=S.call(arguments,1),d=function(){if(this instanceof d){var i=function(){};
i.prototype=f.prototype;
var h=new i();
var g=f.apply(h,c.concat(S.call(arguments)));
if(Object(g)===g){return g
}return h
}else{return f.apply(e,c.concat(S.call(arguments)))
}};
return d
}
}function N(c){M.cssText=c
}function F(d,c){return N(prefixes.join(d+";")+(c||""))
}function I(d,c){return typeof d===c
}function K(d,c){return !!~(""+d).indexOf(c)
}function U(d,g,f){for(var c in d){var e=g[d[c]];
if(e!==G){if(f===false){return d[c]
}if(I(e,"function")){return e.bind(f||g)
}return e
}}return false
}function P(){J.input=(function(e){for(var d=0,c=e.length;
d<c;
d++){R[e[d]]=!!(e[d] in D)
}if(R.list){R.list=!!(Q.createElement("datalist")&&L.HTMLDataListElement)
}return R
})("autocomplete autofocus list placeholder max min multiple pattern required step".split(" "));
J.inputtypes=(function(f){for(var e=0,d,h,g,c=f.length;
e<c;
e++){D.setAttribute("type",h=f[e]);
d=D.type!=="text";
if(d){D.value=X;
D.style.cssText="position:absolute;visibility:hidden;";
if(/^range$/.test(h)&&D.style.WebkitAppearance!==G){Z.appendChild(D);
g=Q.defaultView;
d=g.getComputedStyle&&g.getComputedStyle(D,null).WebkitAppearance!=="textfield"&&(D.offsetHeight!==0);
Z.removeChild(D)
}else{if(/^(search|tel)$/.test(h)){}else{if(/^(url|email)$/.test(h)){d=D.checkValidity&&D.checkValidity()===false
}else{d=D.value!=X
}}}}B[f[e]]=!!d
}return B
})("search tel url email datetime date month week time datetime-local number range color".split(" "))
}for(var E in H){if(Y(H,E)){A=E.toLowerCase();
J[A]=H[E]();
V.push((J[A]?"":"no-")+A)
}}J.input||P();
J.addTest=function(d,e){if(typeof d=="object"){for(var c in d){if(Y(d,c)){J.addTest(c,d[c])
}}}else{d=d.toLowerCase();
if(J[d]!==G){return J
}e=typeof e=="function"?e():e;
if(typeof enableClasses!=="undefined"&&enableClasses){Z.className+=" "+(e?"":"no-")+d
}J[d]=e
}return J
};
N("");
W=D=null;
J._version=C;
return J
})(this,this.document);
(function(){(function(A){A.fn.inputDate=function(){var D,B,F,C,G,E;
G=function(M){var K,I,H,J,L;
if(/^\d{4,}-\d\d-\d\d$/.test(M)){H=/^(\d+)-(\d+)-(\d+)$/.exec(M);
L=parseInt(H[1],10);
J=parseInt(H[2],10);
I=parseInt(H[3],10);
K=new Date(L,J-1,I);
return K
}else{throw"Invalid date string: "+M
}};
C=function(H){var I;
I=[H.getFullYear().toString()];
I.push("-");
if(H.getMonth()<9){I.push("0")
}I.push((H.getMonth()+1).toString());
I.push("-");
if(H.getDate()<10){I.push("0")
}I.push(H.getDate().toString());
return I.join("")
};
F=function(H,L){var I,J,M,K;
I=A(L);
M=I.datepicker("option","dayNames");
K=I.datepicker("option","monthNames");
J=[M[H.getDay()]];
J.push(", ");
J.push(K[H.getMonth()]);
J.push(" ");
J.push(H.getDate().toString());
J.push(", ");
J.push(H.getFullYear().toString());
return J.join("")
};
B=function(I,N,M){var J,H,K,L;
J=A(I);
L=G(J.val());
K=J.data("step");
H=J.data("max");
if(!(K!=null)||K==="any"){L.setDate(L.getDate()+1)
}else{L.setDate(L.getDate()+K)
}if((H!=null)&&L>H){L.setTime(H.getTime())
}L=E(L,I);
J.val(C(L)).change();
A(N).text(F(L,M));
A(M).datepicker("setDate",L);
return null
};
D=function(H,N,M){var J,I,K,L;
J=A(H);
L=G(J.val());
K=J.data("step");
I=J.data("min");
if(!(K!=null)||K==="any"){L.setDate(L.getDate()-1)
}else{L.setDate(L.getDate()-K)
}if((I!=null)&&L<I){L.setTime(I.getTime())
}L=E(L,H);
J.val(C(L)).change();
A(N).text(F(L,M));
A(M).datepicker("setDate",L);
return null
};
E=function(L,N){var H,P,R,O,I,M,J,Q,K;
H=A(N);
J=H.data("step");
O=H.data("min");
R=H.data("max");
if((J!=null)&&J!=="any"){P=L.getTime();
M=J*86400000;
if(O==null){O=new Date(1970,0,1)
}I=O.getTime();
Q=(P-I)%M;
K=M-Q;
if(Q===0){return L
}else{if(Q>K){return new Date(L.getTime()+K)
}else{return new Date(L.getTime()-Q)
}}}else{return L
}};
A(this).filter('input[type="date"]').each(function(){var U,S,K,I,P,W,V,N,O,R,L,Q,M,J,H,T;
P=A(this);
T=P.attr("value");
M=P.attr("min");
Q=P.attr("max");
J=P.attr("step");
N=P.attr("class");
H=P.attr("style");
if((T!=null)&&/^\d{4,}-\d\d-\d\d$/.test(T)){T=G(T)
}else{T=new Date()
}if(M!=null){M=G(M);
if(T<M){T.setTime(M.getTime())
}}if(Q!=null){Q=G(Q);
if(T>Q){T.setTime(Q.getTime())
}}if((J!=null)&&J!=="any"){J=parseInt(J,10)
}L=document.createElement("input");
I=A(L);
I.attr({type:"hidden",name:P.attr("name"),value:C(T)});
I.data({min:M,max:Q,step:J});
T=E(T,L);
I.attr("value",C(T));
W=document.createElement("span");
U=A(W);
if(N!=null){U.attr("class",N)
}if(H!=null){U.attr("style",H)
}V=document.createElement("div");
S=A(V);
S.css({display:"none",position:"absolute"});
R=document.createElement("button");
K=A(R);
K.addClass("date-datepicker-button");
P.replaceWith(L);
U.insertAfter(L);
K.appendTo(W);
S.appendTo(W);
S.datepicker({dateFormat:"MM dd, yy",showButtonPanel:true,beforeShowDay:function(X){var Z,Y;
if(!(J!=null)||J==="any"){return[true,""]
}else{if(M==null){M=new Date(1970,0,1)
}Z=Math.floor(X.getTime()/86400000);
Y=Math.floor(M.getTime()/86400000);
return[(Z-Y)%J===0,""]
}}});
K.text(F(T,V));
if(M!=null){S.datepicker("option","minDate",M)
}if(Q!=null){S.datepicker("option","maxDate",Q)
}if(Modernizr.csstransitions){V.className="date-calendar-dialog date-closed";
K.click(function(X){S.off("transitionend oTransitionEnd webkitTransitionEnd MSTransitionEnd");
V.style.display="block";
V.className="date-calendar-dialog date-open";
X.preventDefault();
return false
});
O=function(X){var Y;
if(V.className==="date-calendar-dialog date-open"){Y=function(Z,a){V.style.display="none";
S.off("transitionend oTransitionEnd webkitTransitionEnd MSTransitionEnd",Y);
return null
};
S.on("transitionend oTransitionEnd webkitTransitionEnd MSTransitionEnd",Y);
V.className="date-calendar-dialog date-closed"
}if(X!=null){X.preventDefault()
}return null
}
}else{K.click(function(X){S.fadeIn("fast");
X.preventDefault();
return false
});
O=function(X){S.fadeOut("fast");
if(X!=null){X.preventDefault()
}return null
}
}S.mouseleave(O);
S.datepicker("option","onSelect",function(Z,Y){var X;
X=A.datepicker.parseDate("MM dd, yy",Z);
I.val(C(X)).change();
K.text(F(X,V));
O();
return null
});
S.datepicker("setDate",T);
K.on({DOMMouseScroll:function(X){if(X.originalEvent.detail<0){B(L,R,V)
}else{D(L,R,V)
}X.preventDefault();
return null
},mousewheel:function(X){if(X.originalEvent.wheelDelta>0){B(L,R,V)
}else{D(L,R,V)
}X.preventDefault();
return null
},keypress:function(X){if(X.keyCode===38){B(L,R,V);
X.preventDefault()
}else{if(X.keyCode===40){D(L,R,V);
X.preventDefault()
}}return null
}});
return null
});
return this
};
A(function(){if(!Modernizr.inputtypes.date){A('input[type="date"]').inputDate()
}return null
});
return null
})(jQuery)
}).call(this);
(function(){(function(A){A.fn.inputDateTimeLocal=function(){var D,G,I,J,C,H,B,E,F;
E=function(O){var S,R,Q,P,M,L,T,K,N;
if(/^\d{4,}-\d\d-\d\dT\d\d:\d\d(?:\:\d\d(?:\.\d+)?)?$/.test(O)){P=/^(\d+)-(\d+)-(\d+)T(\d+):(\d+)(?:\:(\d+)(?:\.(\d+))?)?$/.exec(O);
N=parseInt(P[1],10);
T=parseInt(P[2],10);
R=parseInt(P[3],10);
Q=parseInt(P[4],10);
L=parseInt(P[5],10);
K=P[6]!=null?parseInt(P[6],10):0;
M=P[7]!=null?P[7]:"0";
while(M.length<3){M+="0"
}if(M.length>3){M=M.substring(0,3)
}M=parseInt(M,10);
S=new Date();
S.setFullYear(N);
S.setMonth(T-1);
S.setDate(R);
S.setHours(Q);
S.setMinutes(L);
S.setSeconds(K);
S.setMilliseconds(M);
return S
}else{throw"Invalid datetime string: "+O
}};
H=function(K){var L;
L=[K.getFullYear().toString()];
L.push("-");
if(K.getMonth()<9){L.push("0")
}L.push((K.getMonth()+1).toString());
L.push("-");
if(K.getDate()<10){L.push("0")
}L.push(K.getDate().toString());
L.push("T");
if(K.getHours()<10){L.push("0")
}L.push(K.getHours().toString());
L.push(":");
if(K.getMinutes()<10){L.push("0")
}L.push(K.getMinutes().toString());
if(K.getSeconds()>0||K.getMilliseconds()>0){L.push(":");
if(K.getSeconds()<10){L.push("0")
}L.push(K.getSeconds().toString());
if(K.getMilliseconds()>0){L.push(".");
if(K.getMilliseconds()<100){L.push("0")
}if(K.getMilliseconds()<10){L.push("0")
}L.push(K.getMilliseconds().toString())
}}return L.join("")
};
C=function(K,O){var L,M,P,N;
L=A(O);
P=L.datepicker("option","dayNames");
N=L.datepicker("option","monthNames");
M=[P[K.getDay()]];
M.push(", ");
M.push(N[K.getMonth()]);
M.push(" ");
M.push(K.getDate().toString());
M.push(", ");
M.push(K.getFullYear().toString());
return M.join("")
};
B=function(K){var L,M;
M=new Array();
if(K.getHours()===0){M.push("12");
L="AM"
}else{if(K.getHours()>0&&K.getHours()<10){M.push("0");
M.push(K.getHours().toString());
L="AM"
}else{if(K.getHours()>=10&&K.getHours()<12){M.push(K.getHours().toString());
L="AM"
}else{if(K.getHours()===12){M.push("12");
L="PM"
}else{if(K.getHours()>12&&K.getHours()<22){M.push("0");
M.push((K.getHours()-12).toString());
L="PM"
}else{if(K.getHours()>=22){M.push((K.getHours()-12).toString());
L="PM"
}}}}}}M.push(":");
if(K.getMinutes()<10){M.push("0")
}M.push(K.getMinutes().toString());
M.push(":");
if(K.getSeconds()<10){M.push("0")
}M.push(K.getSeconds().toString());
if(K.getMilliseconds()>0){M.push(".");
if(K.getMilliseconds()%100===0){M.push((K.getMilliseconds()/100).toString())
}else{if(K.getMilliseconds()%10===0){M.push("0");
M.push((K.getMilliseconds()/10).toString())
}else{if(K.getMilliseconds()<100){M.push("0")
}if(K.getMilliseconds()<10){M.push("0")
}M.push(K.getMilliseconds().toString())
}}}M.push(" ");
M.push(L);
return M.join("")
};
I=function(L,R,O,Q){var M,K,N,P;
M=A(L);
P=E(M.val());
N=M.data("step");
K=M.data("max");
if(!(N!=null)||N==="any"){P.setSeconds(P.getSeconds()+1)
}else{P.setSeconds(P.getSeconds()+N)
}if((K!=null)&&P>K){P.setTime(K.getTime())
}M.val(H(P)).change();
A(R).text(C(P,Q));
A(O).val(B(P));
A(Q).datepicker("setDate",P);
return null
};
D=function(K,R,O,Q){var M,L,N,P;
M=A(K);
P=E(M.val());
N=M.data("step");
L=M.data("min");
if(!(N!=null)||N==="any"){P.setSeconds(P.getSeconds()-1)
}else{P.setSeconds(P.getSeconds()-N)
}if((L!=null)&&P<L){P.setTime(L.getTime())
}M.val(H(P)).change();
A(R).text(C(P,Q));
A(O).val(B(P));
A(Q).datepicker("setDate",P);
return null
};
J=function(L,R,O,Q){var M,K,N,P;
M=A(L);
P=E(M.val());
N=M.data("step");
K=M.data("max");
P.setDate(P.getDate()+1);
if((K!=null)&&P>K){P.setTime(K.getTime())
}M.val(H(P)).change();
A(R).text(C(P,Q));
A(O).val(B(P));
A(Q).datepicker("setDate",P);
return null
};
G=function(K,R,O,Q){var M,L,N,P;
M=A(K);
P=E(M.val());
N=M.data("step");
L=M.data("min");
P.setDate(P.getDate()-1);
if((L!=null)&&P<L){P.setTime(L.getTime())
}M.val(H(P)).change();
A(R).text(C(P,Q));
A(O).val(B(P));
A(Q).datepicker("setDate",P);
return null
};
F=function(O,Q){var K,S,U,R,L,P,M,T,N;
K=A(Q);
M=K.data("step");
R=K.data("min");
U=K.data("max");
if((M!=null)&&M!=="any"){S=O.getTime();
P=M*1000;
if(R==null){R=new Date(0)
}L=R.getTime();
T=(S-L)%P;
N=P-T;
if(T===0){return O
}else{if(T>N){return new Date(O.getTime()+N)
}else{return new Date(O.getTime()-T)
}}}else{return O
}};
A(this).filter('input[type="datetime-local"]').each(function(){var U,T,Y,R,P,X,a,O,S,K,e,M,L,W,Q,c,b,N,d,f,V,Z;
P=A(this);
Z=P.attr("value");
b=P.attr("min");
c=P.attr("max");
N=P.attr("step");
K=P.attr("class");
d=P.attr("style");
if((Z!=null)&&/^\d{4,}-\d\d-\d\dT\d\d:\d\d(?:\:\d\d(?:\.\d+)?)?$/.test(Z)){Z=E(Z)
}else{Z=new Date()
}if(b!=null){b=E(b);
if(Z<b){Z.setTime(b.getTime())
}}if(c!=null){c=E(c);
if(Z>c){Z.setTime(c.getTime())
}}if((N!=null)&&N!=="any"){N=parseFloat(N)
}Q=document.createElement("input");
R=A(Q);
R.attr({type:"hidden",name:P.attr("name"),value:H(Z)});
R.data({min:b,max:c,step:N});
Z=F(Z,Q);
R.attr("value",H(Z));
O=document.createElement("span");
U=A(O);
if(K!=null){U.attr("class",K)
}if(d!=null){U.attr("style",d)
}S=document.createElement("div");
T=A(S);
T.css({display:"none",position:"absolute"});
M=document.createElement("button");
Y=A(M);
Y.addClass("datetime-local-datepicker-button");
f=document.createElement("input");
X=A(f);
X.attr({type:"text",value:B(Z),size:14});
P.replaceWith(Q);
Y.appendTo(O);
T.appendTo(O);
U.insertAfter(Q);
X.insertAfter(O);
W=(X.outerHeight()/2)+"px";
V=document.createElement("div");
A(V).addClass("datetime-local-spin-btn datetime-local-spin-btn-up").css("height",W);
L=document.createElement("div");
A(L).addClass("datetime-local-spin-btn datetime-local-spin-btn-down").css("height",W);
a=document.createElement("div");
a.appendChild(V);
a.appendChild(L);
A(a).addClass("datetime-local-spin-btn-container").insertAfter(f);
T.datepicker({dateFormat:"MM dd, yy",showButtonPanel:true});
Y.text(C(Z,S));
if(b!=null){T.datepicker("option","minDate",b)
}if(c!=null){T.datepicker("option","maxDate",c)
}if(Modernizr.csstransitions){S.className="datetime-local-calendar-dialog datetime-local-closed";
Y.click(function(g){T.off("transitionend oTransitionEnd webkitTransitionEnd MSTransitionEnd");
S.style.display="block";
S.className="datetime-local-calendar-dialog datetime-local-open";
g.preventDefault();
return false
});
e=function(g){var h;
if(S.className==="datetime-local-calendar-dialog datetime-local-open"){h=function(i,j){S.style.display="none";
T.off("transitionend oTransitionEnd webkitTransitionEnd MSTransitionEnd",h);
return null
};
T.on("transitionend oTransitionEnd webkitTransitionEnd MSTransitionEnd",h);
S.className="datetime-local-calendar-dialog datetime-local-closed"
}if(g!=null){g.preventDefault()
}return null
}
}else{Y.click(function(g){T.fadeIn("fast");
g.preventDefault();
return false
});
e=function(g){T.fadeOut("fast");
if(g!=null){g.preventDefault()
}return null
}
}T.mouseleave(e);
T.datepicker("option","onSelect",function(j,i){var g,h;
h=E(R.val());
g=A.datepicker.parseDate("MM dd, yy",j);
g.setHours(h.getHours());
g.setMinutes(h.getMinutes());
g.setSeconds(h.getSeconds());
g.setMilliseconds(h.getMilliseconds());
if((b!=null)&&g<b){g.setTime(b.getTime())
}else{if((c!=null)&&g>c){g.setTime(c.getTime())
}}g=F(g,Q);
R.val(H(g)).change();
X.val(B(g));
Y.text(C(g,S));
e();
return null
});
T.datepicker("setDate",Z);
Y.on({DOMMouseScroll:function(g){if(g.originalEvent.detail<0){J(Q,M,f,S)
}else{G(Q,M,f,S)
}g.preventDefault();
return null
},mousewheel:function(g){if(g.originalEvent.wheelDelta>0){J(Q,M,f,S)
}else{G(Q,M,f,S)
}g.preventDefault();
return null
},keypress:function(g){if(g.keyCode===38){J(Q,M,f,S);
g.preventDefault()
}else{if(g.keyCode===40){G(Q,M,f,S);
g.preventDefault()
}}return null
}});
X.on({DOMMouseScroll:function(g){if(g.originalEvent.detail<0){I(Q,M,f,S)
}else{D(Q,M,f,S)
}g.preventDefault();
return null
},mousewheel:function(g){if(g.originalEvent.wheelDelta>0){I(Q,M,f,S)
}else{D(Q,M,f,S)
}g.preventDefault();
return null
},keypress:function(h){var i,g;
if(h.keyCode===38){I(Q,M,f,S);
h.preventDefault()
}else{if(h.keyCode===40){D(Q,M,f,S);
h.preventDefault()
}else{if(((i=h.keyCode)!==35&&i!==36&&i!==37&&i!==39&&i!==46)&&((g=h.which)!==8&&g!==9&&g!==32&&g!==45&&g!==46&&g!==47&&g!==48&&g!==49&&g!==50&&g!==51&&g!==52&&g!==53&&g!==54&&g!==55&&g!==56&&g!==57&&g!==58&&g!==65&&g!==77&&g!==80&&g!==97&&g!==109&&g!==112)){h.preventDefault()
}}}return null
},change:function(m){var k,i,h,g,j,l,n;
P=A(this);
if(/^((?:1[0-2])|(?:0[1-9]))\:[0-5]\d(?:\:[0-5]\d(?:\.\d+)?)?\s[AaPp][Mm]$/.test(P.val())){g=/^(\d\d):(\d\d)(?:\:(\d\d)(?:\.(\d+))?)?\s([AaPp][Mm])$/.exec(P.val());
h=parseInt(g[1],10);
l=parseInt(g[2],10);
n=parseInt(g[3],10)||0;
j=g[4];
if(j==null){j=0
}else{if(j.length>3){j=parseInt(j.substring(0,3),10)
}else{if(j.length<3){while(j.length<3){j+="0"
}j=parseInt(j,10)
}else{j=parseInt(j,10)
}}}k=g[5].toUpperCase();
i=E(R.val());
if(k==="AM"&&h===12){h=0
}else{if(k==="PM"&&h!==12){h+=12
}}i.setHours(h);
i.setMinutes(l);
i.setSeconds(n);
i.setMilliseconds(j);
if((b!=null)&&i<b){R.val(H(b)).change();
P.val(B(b))
}else{if((c!=null)&&i>c){R.val(H(c)).change();
P.val(B(c))
}else{i=F(i,Q);
R.val(H(i)).change();
P.val(B(i))
}}}else{P.val(B(E(R.val())))
}return null
}});
A(V).on("mousedown",function(h){var i,g;
I(Q,M,f,S);
g=function(j,n,l,m,k){k(j,n,l,m);
A(l).data("timeoutID",window.setTimeout(g,10,j,n,l,m,k));
return null
};
i=function(j){window.clearTimeout(A(f).data("timeoutID"));
A(document).off("mouseup",i);
A(V).off("mouseleave",i);
return null
};
A(document).on("mouseup",i);
A(V).on("mouseleave",i);
A(f).data("timeoutID",window.setTimeout(g,700,Q,M,f,S,I));
return null
});
A(L).on("mousedown",function(h){var i,g;
D(Q,M,f,S);
g=function(j,m,k,l,n){n(j,m,k,l);
A(k).data("timeoutID",window.setTimeout(g,10,j,m,k,l,n));
return null
};
i=function(j){window.clearTimeout(A(f).data("timeoutID"));
A(document).off("mouseup",i);
A(L).off("mouseleave",i);
return null
};
A(document).on("mouseup",i);
A(L).on("mouseleave",i);
A(f).data("timeoutID",window.setTimeout(g,700,Q,M,f,S,D));
return null
});
return null
});
return this
};
A(function(){if(!Modernizr.inputtypes["datetime-local"]){A('input[type="datetime-local"]').inputDateTimeLocal()
}return null
});
return null
})(jQuery)
}).call(this);
(function(A){A.flexslider=function(D,N){var B=A(D),L=A.extend({},A.flexslider.defaults,N),G=L.namespace,I=("ontouchstart" in window)||window.DocumentTouch&&document instanceof DocumentTouch,C=(I)?"touchend":"click",H=L.direction==="vertical",J=L.reverse,M=(L.itemWidth>0),F=L.animation==="fade",K=L.asNavFor!=="",E={};
A.data(D,"flexslider",B);
E={init:function(){B.animating=false;
B.currentSlide=L.startAt;
B.animatingTo=B.currentSlide;
B.atEnd=(B.currentSlide===0||B.currentSlide===B.last);
B.containerSelector=L.selector.substr(0,L.selector.search(" "));
B.slides=A(L.selector,B);
B.container=A(B.containerSelector,B);
B.count=B.slides.length;
B.syncExists=A(L.sync).length>0;
if(L.animation==="slide"){L.animation="swing"
}B.prop=(H)?"top":"marginLeft";
B.args={};
B.manualPause=false;
B.transitions=!L.video&&!F&&L.useCSS&&(function(){var Q=document.createElement("div"),P=["perspectiveProperty","WebkitPerspective","MozPerspective","OPerspective","msPerspective"];
for(var O in P){if(Q.style[P[O]]!==undefined){B.pfx=P[O].replace("Perspective","").toLowerCase();
B.prop="-"+B.pfx+"-transform";
return true
}}return false
}());
if(L.controlsContainer!==""){B.controlsContainer=A(L.controlsContainer).length>0&&A(L.controlsContainer)
}if(L.manualControls!==""){B.manualControls=A(L.manualControls).length>0&&A(L.manualControls)
}if(L.randomize){B.slides.sort(function(){return(Math.round(Math.random())-0.5)
});
B.container.empty().append(B.slides)
}B.doMath();
if(K){E.asNav.setup()
}B.setup("init");
if(L.controlNav){E.controlNav.setup()
}if(L.directionNav){E.directionNav.setup()
}if(L.keyboard&&(A(B.containerSelector).length===1||L.multipleKeyboard)){A(document).bind("keyup",function(P){var O=P.keyCode;
if(!B.animating&&(O===39||O===37)){var Q=(O===39)?B.getTarget("next"):(O===37)?B.getTarget("prev"):false;
B.flexAnimate(Q,L.pauseOnAction)
}})
}if(L.mousewheel){B.bind("mousewheel",function(Q,S,P,O){Q.preventDefault();
var R=(S<0)?B.getTarget("next"):B.getTarget("prev");
B.flexAnimate(R,L.pauseOnAction)
})
}if(L.pausePlay){E.pausePlay.setup()
}if(L.slideshow){if(L.pauseOnHover){B.hover(function(){if(!B.manualPlay&&!B.manualPause){B.pause()
}},function(){if(!B.manualPause&&!B.manualPlay){B.play()
}})
}(L.initDelay>0)?setTimeout(B.play,L.initDelay):B.play()
}if(I&&L.touch){E.touch()
}if(!F||(F&&L.smoothHeight)){A(window).bind("resize focus",E.resize)
}setTimeout(function(){L.start(B)
},200)
},asNav:{setup:function(){B.asNav=true;
B.animatingTo=Math.floor(B.currentSlide/B.move);
B.currentItem=B.currentSlide;
B.slides.removeClass(G+"active-slide").eq(B.currentItem).addClass(G+"active-slide");
B.slides.click(function(Q){Q.preventDefault();
var P=A(this),O=P.index();
if(!A(L.asNavFor).data("flexslider").animating&&!P.hasClass("active")){B.direction=(B.currentItem<O)?"next":"prev";
B.flexAnimate(O,L.pauseOnAction,false,true,true)
}})
}},controlNav:{setup:function(){if(!B.manualControls){E.controlNav.setupPaging()
}else{E.controlNav.setupManual()
}},setupPaging:function(){var Q=(L.controlNav==="thumbnails")?"control-thumbs":"control-paging",O=1,R;
B.controlNavScaffold=A('<ol class="'+G+"control-nav "+G+Q+'"></ol>');
if(B.pagingCount>1){for(var P=0;
P<B.pagingCount;
P++){R=(L.controlNav==="thumbnails")?'<img src="'+B.slides.eq(P).attr("data-thumb")+'"/>':"<a>"+O+"</a>";
B.controlNavScaffold.append("<li>"+R+"</li>");
O++
}}(B.controlsContainer)?A(B.controlsContainer).append(B.controlNavScaffold):B.append(B.controlNavScaffold);
E.controlNav.set();
E.controlNav.active();
B.controlNavScaffold.delegate("a, img",C,function(S){S.preventDefault();
var U=A(this),T=B.controlNav.index(U);
if(!U.hasClass(G+"active")){B.direction=(T>B.currentSlide)?"next":"prev";
B.flexAnimate(T,L.pauseOnAction)
}});
if(I){B.controlNavScaffold.delegate("a","click touchstart",function(S){S.preventDefault()
})
}},setupManual:function(){B.controlNav=B.manualControls;
E.controlNav.active();
B.controlNav.live(C,function(O){O.preventDefault();
var Q=A(this),P=B.controlNav.index(Q);
if(!Q.hasClass(G+"active")){(P>B.currentSlide)?B.direction="next":B.direction="prev";
B.flexAnimate(P,L.pauseOnAction)
}});
if(I){B.controlNav.live("click touchstart",function(O){O.preventDefault()
})
}},set:function(){var O=(L.controlNav==="thumbnails")?"img":"a";
B.controlNav=A("."+G+"control-nav li "+O,(B.controlsContainer)?B.controlsContainer:B)
},active:function(){B.controlNav.removeClass(G+"active").eq(B.animatingTo).addClass(G+"active")
},update:function(O,P){if(B.pagingCount>1&&O==="add"){B.controlNavScaffold.append(A("<li><a>"+B.count+"</a></li>"))
}else{if(B.pagingCount===1){B.controlNavScaffold.find("li").remove()
}else{B.controlNav.eq(P).closest("li").remove()
}}E.controlNav.set();
(B.pagingCount>1&&B.pagingCount!==B.controlNav.length)?B.update(P,O):E.controlNav.active()
}},directionNav:{setup:function(){var O=A('<ul class="'+G+'direction-nav"><li><a class="'+G+'prev" href="#">'+L.prevText+'</a></li><li><a class="'+G+'next" href="#">'+L.nextText+"</a></li></ul>");
if(B.controlsContainer){A(B.controlsContainer).append(O);
B.directionNav=A("."+G+"direction-nav li a",B.controlsContainer)
}else{B.append(O);
B.directionNav=A("."+G+"direction-nav li a",B)
}E.directionNav.update();
B.directionNav.bind(C,function(P){P.preventDefault();
var Q=(A(this).hasClass(G+"next"))?B.getTarget("next"):B.getTarget("prev");
B.flexAnimate(Q,L.pauseOnAction)
});
if(I){B.directionNav.bind("click touchstart",function(P){P.preventDefault()
})
}},update:function(){var O=G+"disabled";
if(B.pagingCount===1){B.directionNav.addClass(O)
}else{if(!L.animationLoop){if(B.animatingTo===0){B.directionNav.removeClass(O).filter("."+G+"prev").addClass(O)
}else{if(B.animatingTo===B.last){B.directionNav.removeClass(O).filter("."+G+"next").addClass(O)
}else{B.directionNav.removeClass(O)
}}}else{B.directionNav.removeClass(O)
}}}},pausePlay:{setup:function(){var O=A('<div class="'+G+'pauseplay"><a></a></div>');
if(B.controlsContainer){B.controlsContainer.append(O);
B.pausePlay=A("."+G+"pauseplay a",B.controlsContainer)
}else{B.append(O);
B.pausePlay=A("."+G+"pauseplay a",B)
}E.pausePlay.update((L.slideshow)?G+"pause":G+"play");
B.pausePlay.bind(C,function(P){P.preventDefault();
if(A(this).hasClass(G+"pause")){B.manualPause=true;
B.manualPlay=false;
B.pause()
}else{B.manualPause=false;
B.manualPlay=true;
B.play()
}});
if(I){B.pausePlay.bind("click touchstart",function(P){P.preventDefault()
})
}},update:function(O){(O==="play")?B.pausePlay.removeClass(G+"pause").addClass(G+"play").text(L.playText):B.pausePlay.removeClass(G+"play").addClass(G+"pause").text(L.pauseText)
}},touch:function(){var T,R,P,U,X,V,S=false;
D.addEventListener("touchstart",Q,false);
function Q(Y){if(B.animating){Y.preventDefault()
}else{if(Y.touches.length===1){B.pause();
U=(H)?B.h:B.w;
V=Number(new Date());
P=(M&&J&&B.animatingTo===B.last)?0:(M&&J)?B.limit-(((B.itemW+L.itemMargin)*B.move)*B.animatingTo):(M&&B.currentSlide===B.last)?B.limit:(M)?((B.itemW+L.itemMargin)*B.move)*B.currentSlide:(J)?(B.last-B.currentSlide+B.cloneOffset)*U:(B.currentSlide+B.cloneOffset)*U;
T=(H)?Y.touches[0].pageY:Y.touches[0].pageX;
R=(H)?Y.touches[0].pageX:Y.touches[0].pageY;
D.addEventListener("touchmove",O,false);
D.addEventListener("touchend",W,false)
}}}function O(Y){X=(H)?T-Y.touches[0].pageY:T-Y.touches[0].pageX;
S=(H)?(Math.abs(X)<Math.abs(Y.touches[0].pageX-R)):(Math.abs(X)<Math.abs(Y.touches[0].pageY-R));
if(!S||Number(new Date())-V>500){Y.preventDefault();
if(!F&&B.transitions){if(!L.animationLoop){X=X/((B.currentSlide===0&&X<0||B.currentSlide===B.last&&X>0)?(Math.abs(X)/U+2):1)
}B.setProps(P+X,"setTouch")
}}}function W(a){D.removeEventListener("touchmove",O,false);
if(B.animatingTo===B.currentSlide&&!S&&!(X===null)){var Z=(J)?-X:X,Y=(Z>0)?B.getTarget("next"):B.getTarget("prev");
if(B.canAdvance(Y)&&(Number(new Date())-V<550&&Math.abs(Z)>50||Math.abs(Z)>U/2)){B.flexAnimate(Y,L.pauseOnAction)
}else{if(!F){B.flexAnimate(B.currentSlide,L.pauseOnAction,true)
}}}D.removeEventListener("touchend",W,false);
T=null;
R=null;
X=null;
P=null
}},resize:function(){if(!B.animating&&B.is(":visible")){if(!M){B.doMath()
}if(F){E.smoothHeight()
}else{if(M){B.slides.width(B.computedW);
B.update(B.pagingCount);
B.setProps()
}else{if(H){B.viewport.height(B.h);
B.setProps(B.h,"setTotal")
}else{if(L.smoothHeight){E.smoothHeight()
}B.newSlides.width(B.computedW);
B.setProps(B.computedW,"setTotal")
}}}}},smoothHeight:function(O){if(!H||F){var P=(F)?B:B.viewport;
(O)?P.animate({height:B.slides.eq(B.animatingTo).height()},O):P.height(B.slides.eq(B.animatingTo).height())
}},sync:function(O){var Q=A(L.sync).data("flexslider"),P=B.animatingTo;
switch(O){case"animate":Q.flexAnimate(P,L.pauseOnAction,false,true);
break;
case"play":if(!Q.playing&&!Q.asNav){Q.play()
}break;
case"pause":Q.pause();
break
}}};
B.flexAnimate=function(W,X,Q,S,T){if(K&&B.pagingCount===1){B.direction=(B.currentItem<W)?"next":"prev"
}if(!B.animating&&(B.canAdvance(W,T)||Q)&&B.is(":visible")){if(K&&S){var P=A(L.asNavFor).data("flexslider");
B.atEnd=W===0||W===B.count-1;
P.flexAnimate(W,true,false,true,T);
B.direction=(B.currentItem<W)?"next":"prev";
P.direction=B.direction;
if(Math.ceil((W+1)/B.visible)-1!==B.currentSlide&&W!==0){B.currentItem=W;
B.slides.removeClass(G+"active-slide").eq(W).addClass(G+"active-slide");
W=Math.floor(W/B.visible)
}else{B.currentItem=W;
B.slides.removeClass(G+"active-slide").eq(W).addClass(G+"active-slide");
return false
}}B.animating=true;
B.animatingTo=W;
L.before(B);
if(X){B.pause()
}if(B.syncExists&&!T){E.sync("animate")
}if(L.controlNav){E.controlNav.active()
}if(!M){B.slides.removeClass(G+"active-slide").eq(W).addClass(G+"active-slide")
}B.atEnd=W===0||W===B.last;
if(L.directionNav){E.directionNav.update()
}if(W===B.last){L.end(B);
if(!L.animationLoop){B.pause()
}}if(!F){var V=(H)?B.slides.filter(":first").height():B.computedW,U,R,O;
if(M){U=(L.itemWidth>B.w)?L.itemMargin*2:L.itemMargin;
O=((B.itemW+U)*B.move)*B.animatingTo;
R=(O>B.limit&&B.visible!==1)?B.limit:O
}else{if(B.currentSlide===0&&W===B.count-1&&L.animationLoop&&B.direction!=="next"){R=(J)?(B.count+B.cloneOffset)*V:0
}else{if(B.currentSlide===B.last&&W===0&&L.animationLoop&&B.direction!=="prev"){R=(J)?0:(B.count+1)*V
}else{R=(J)?((B.count-1)-W+B.cloneOffset)*V:(W+B.cloneOffset)*V
}}}B.setProps(R,"",L.animationSpeed);
if(B.transitions){if(!L.animationLoop||!B.atEnd){B.animating=false;
B.currentSlide=B.animatingTo
}B.container.unbind("webkitTransitionEnd transitionend");
B.container.bind("webkitTransitionEnd transitionend",function(){B.wrapup(V)
})
}else{B.container.animate(B.args,L.animationSpeed,L.easing,function(){B.wrapup(V)
})
}}else{if(!I){B.slides.eq(B.currentSlide).fadeOut(L.animationSpeed,L.easing);
B.slides.eq(W).fadeIn(L.animationSpeed,L.easing,B.wrapup)
}else{B.slides.eq(B.currentSlide).css({opacity:0,zIndex:1});
B.slides.eq(W).css({opacity:1,zIndex:2});
B.slides.unbind("webkitTransitionEnd transitionend");
B.slides.eq(B.currentSlide).bind("webkitTransitionEnd transitionend",function(){L.after(B)
});
B.animating=false;
B.currentSlide=B.animatingTo
}}if(L.smoothHeight){E.smoothHeight(L.animationSpeed)
}}};
B.wrapup=function(O){if(!F&&!M){if(B.currentSlide===0&&B.animatingTo===B.last&&L.animationLoop){B.setProps(O,"jumpEnd")
}else{if(B.currentSlide===B.last&&B.animatingTo===0&&L.animationLoop){B.setProps(O,"jumpStart")
}}}B.animating=false;
B.currentSlide=B.animatingTo;
L.after(B)
};
B.animateSlides=function(){if(!B.animating){B.flexAnimate(B.getTarget("next"))
}};
B.pause=function(){clearInterval(B.animatedSlides);
B.playing=false;
if(L.pausePlay){E.pausePlay.update("play")
}if(B.syncExists){E.sync("pause")
}};
B.play=function(){B.animatedSlides=setInterval(B.animateSlides,L.slideshowSpeed);
B.playing=true;
if(L.pausePlay){E.pausePlay.update("pause")
}if(B.syncExists){E.sync("play")
}};
B.canAdvance=function(Q,O){var P=(K)?B.pagingCount-1:B.last;
return(O)?true:(K&&B.currentItem===B.count-1&&Q===0&&B.direction==="prev")?true:(K&&B.currentItem===0&&Q===B.pagingCount-1&&B.direction!=="next")?false:(Q===B.currentSlide&&!K)?false:(L.animationLoop)?true:(B.atEnd&&B.currentSlide===0&&Q===P&&B.direction!=="next")?false:(B.atEnd&&B.currentSlide===P&&Q===0&&B.direction==="next")?false:true
};
B.getTarget=function(O){B.direction=O;
if(O==="next"){return(B.currentSlide===B.last)?0:B.currentSlide+1
}else{return(B.currentSlide===0)?B.last:B.currentSlide-1
}};
B.setProps=function(R,O,P){var Q=(function(){var S=(R)?R:((B.itemW+L.itemMargin)*B.move)*B.animatingTo,T=(function(){if(M){return(O==="setTouch")?R:(J&&B.animatingTo===B.last)?0:(J)?B.limit-(((B.itemW+L.itemMargin)*B.move)*B.animatingTo):(B.animatingTo===B.last)?B.limit:S
}else{switch(O){case"setTotal":return(J)?((B.count-1)-B.currentSlide+B.cloneOffset)*R:(B.currentSlide+B.cloneOffset)*R;
case"setTouch":return(J)?R:R;
case"jumpEnd":return(J)?R:B.count*R;
case"jumpStart":return(J)?B.count*R:R;
default:return R
}}}());
return(T*-1)+"px"
}());
if(B.transitions){Q=(H)?"translate3d(0,"+Q+",0)":"translate3d("+Q+",0,0)";
P=(P!==undefined)?(P/1000)+"s":"0s";
B.container.css("-"+B.pfx+"-transition-duration",P)
}B.args[B.prop]=Q;
if(B.transitions||P===undefined){B.container.css(B.args)
}};
B.setup=function(P){if(!F){var Q,O;
if(P==="init"){B.viewport=A('<div class="'+G+'viewport"></div>').css({overflow:"hidden",position:"relative"}).appendTo(B).append(B.container);
B.cloneCount=0;
B.cloneOffset=0;
if(J){O=A.makeArray(B.slides).reverse();
B.slides=A(O);
B.container.empty().append(B.slides)
}}if(L.animationLoop&&!M){B.cloneCount=2;
B.cloneOffset=1;
if(P!=="init"){B.container.find(".clone").remove()
}B.container.append(B.slides.first().clone().addClass("clone")).prepend(B.slides.last().clone().addClass("clone"))
}B.newSlides=A(L.selector,B);
Q=(J)?B.count-1-B.currentSlide+B.cloneOffset:B.currentSlide+B.cloneOffset;
if(H&&!M){B.container.height((B.count+B.cloneCount)*200+"%").css("position","absolute").width("100%");
setTimeout(function(){B.newSlides.css({display:"block"});
B.doMath();
B.viewport.height(B.h);
B.setProps(Q*B.h,"init")
},(P==="init")?100:0)
}else{B.container.width((B.count+B.cloneCount)*200+"%");
B.setProps(Q*B.computedW,"init");
setTimeout(function(){B.doMath();
B.newSlides.css({width:B.computedW,"float":"left",display:"block"});
if(L.smoothHeight){E.smoothHeight()
}},(P==="init")?100:0)
}}else{B.slides.css({width:"100%","float":"left",marginRight:"-100%",position:"relative"});
if(P==="init"){if(!I){B.slides.eq(B.currentSlide).fadeIn(L.animationSpeed,L.easing)
}else{B.slides.css({opacity:0,display:"block",webkitTransition:"opacity "+L.animationSpeed/1000+"s ease",zIndex:1}).eq(B.currentSlide).css({opacity:1,zIndex:2})
}}if(L.smoothHeight){E.smoothHeight()
}}if(!M){B.slides.removeClass(G+"active-slide").eq(B.currentSlide).addClass(G+"active-slide")
}};
B.doMath=function(){var O=B.slides.first(),R=L.itemMargin,P=L.minItems,Q=L.maxItems;
B.w=B.width();
B.h=O.height();
B.boxPadding=O.outerWidth()-O.width();
if(M){B.itemT=L.itemWidth+R;
B.minW=(P)?P*B.itemT:B.w;
B.maxW=(Q)?Q*B.itemT:B.w;
B.itemW=(B.minW>B.w)?(B.w-(R*P))/P:(B.maxW<B.w)?(B.w-(R*Q))/Q:(L.itemWidth>B.w)?B.w:L.itemWidth;
B.visible=Math.floor(B.w/(B.itemW+R));
B.move=(L.move>0&&L.move<B.visible)?L.move:B.visible;
B.pagingCount=Math.ceil(((B.count-B.visible)/B.move)+1);
B.last=B.pagingCount-1;
B.limit=(B.pagingCount===1)?0:(L.itemWidth>B.w)?((B.itemW+(R*2))*B.count)-B.w-R:((B.itemW+R)*B.count)-B.w-R
}else{B.itemW=B.w;
B.pagingCount=B.count;
B.last=B.count-1
}B.computedW=B.itemW-B.boxPadding
};
B.update=function(P,O){B.doMath();
if(!M){if(P<B.currentSlide){B.currentSlide+=1
}else{if(P<=B.currentSlide&&P!==0){B.currentSlide-=1
}}B.animatingTo=B.currentSlide
}if(L.controlNav&&!B.manualControls){if((O==="add"&&!M)||B.pagingCount>B.controlNav.length){E.controlNav.update("add")
}else{if((O==="remove"&&!M)||B.pagingCount<B.controlNav.length){if(M&&B.currentSlide>B.last){B.currentSlide-=1;
B.animatingTo-=1
}E.controlNav.update("remove",B.last)
}}}if(L.directionNav){E.directionNav.update()
}};
B.addSlide=function(O,Q){var P=A(O);
B.count+=1;
B.last=B.count-1;
if(H&&J){(Q!==undefined)?B.slides.eq(B.count-Q).after(P):B.container.prepend(P)
}else{(Q!==undefined)?B.slides.eq(Q).before(P):B.container.append(P)
}B.update(Q,"add");
B.slides=A(L.selector+":not(.clone)",B);
B.setup();
L.added(B)
};
B.removeSlide=function(O){var P=(isNaN(O))?B.slides.index(A(O)):O;
B.count-=1;
B.last=B.count-1;
if(isNaN(O)){A(O,B.slides).remove()
}else{(H&&J)?B.slides.eq(B.last).remove():B.slides.eq(O).remove()
}B.doMath();
B.update(P,"remove");
B.slides=A(L.selector+":not(.clone)",B);
B.setup();
L.removed(B)
};
E.init()
};
A.flexslider.defaults={namespace:"flex-",selector:".slides > li",animation:"fade",easing:"swing",direction:"horizontal",reverse:false,animationLoop:true,smoothHeight:false,startAt:0,slideshow:true,slideshowSpeed:7000,animationSpeed:600,initDelay:0,randomize:false,pauseOnAction:true,pauseOnHover:false,useCSS:true,touch:true,video:false,controlNav:true,directionNav:true,prevText:"Previous",nextText:"Next",keyboard:true,multipleKeyboard:false,mousewheel:false,pausePlay:false,pauseText:"Pause",playText:"Play",controlsContainer:"",manualControls:"",sync:"",asNavFor:"",itemWidth:0,itemMargin:0,minItems:0,maxItems:0,move:0,start:function(){},before:function(){},after:function(){},end:function(){},added:function(){},removed:function(){}};
A.fn.flexslider=function(B){if(B===undefined){B={}
}if(typeof B==="object"){return this.each(function(){var F=A(this),D=(B.selector)?B.selector:".slides > li",E=F.find(D);
if(E.length===1){E.fadeIn(400);
if(B.start){B.start(F)
}}else{if(F.data("flexslider")==undefined){new A.flexslider(this,B)
}}})
}else{var C=A(this).data("flexslider");
switch(B){case"play":C.play();
break;
case"pause":C.pause();
break;
case"next":C.flexAnimate(C.getTarget("next"),true);
break;
case"prev":case"previous":C.flexAnimate(C.getTarget("prev"),true);
break;
default:if(typeof B==="number"){C.flexAnimate(B,true)
}}}}
})(jQuery);