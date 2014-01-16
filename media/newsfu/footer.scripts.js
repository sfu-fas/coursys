(function(B){B.fn.superfish=function(J){var F=B.fn.superfish,I=F.c,E=B(['<span class="',I.arrowClass,'"> &#187;</span>'].join("")),H=function(){var K=B(this),L=C(K);
clearTimeout(L.sfTimer);
K.showSuperfishUl().siblings().hideSuperfishUl()
},D=function(){var K=B(this),M=C(K),L=F.op;
clearTimeout(M.sfTimer);
M.sfTimer=setTimeout(function(){L.retainPath=(B.inArray(K[0],L.$path)>-1);
K.hideSuperfishUl();
if(L.$path.length&&K.parents(["li.",L.hoverClass].join("")).length<1){H.call(L.$path)
}},L.delay)
},C=function(K){var L=K.parents(["ul.",I.menuClass,":first"].join(""))[0];
F.op=F.o[L.serial];
return L
},G=function(K){K.addClass(I.anchorClass).append(E.clone())
};
return this.each(function(){var K=this.serial=F.o.length;
var M=B.extend({},F.defaults,J);
M.$path=B("li."+M.pathClass,this).slice(0,M.pathLevels).each(function(){B(this).addClass([M.hoverClass,I.bcClass].join(" ")).filter("li:has(ul)").removeClass(M.pathClass)
});
F.o[K]=F.op=M;
B("li:has(ul)",this)[(B.fn.hoverIntent&&!M.disableHI)?"hoverIntent":"hover"](H,D).each(function(){if(M.autoArrows){G(B(">a:first-child",this))
}}).not("."+I.bcClass).hideSuperfishUl();
var L=B("a",this);
L.each(function(N){var O=L.eq(N).parents("li");
L.eq(N).focus(function(){H.call(O)
}).blur(function(){D.call(O)
})
});
M.onInit.call(this)
}).each(function(){var K=[I.menuClass];
if(F.op.dropShadows&&!(B.browser.msie&&B.browser.version<7)){K.push(I.shadowClass)
}B(this).addClass(K.join(" "))
})
};
var A=B.fn.superfish;
A.o=[];
A.op={};
A.IE7fix=function(){var C=A.op;
if(B.browser.msie&&B.browser.version>6&&C.dropShadows&&C.animation.opacity!=undefined){this.toggleClass(A.c.shadowClass+"-off")
}};
A.c={bcClass:"sf-breadcrumb",menuClass:"sf-js-enabled",anchorClass:"sf-with-ul",arrowClass:"sf-sub-indicator",shadowClass:"sf-shadow"};
A.defaults={hoverClass:"sfHover",pathClass:"overideThisToUse",pathLevels:1,delay:800,animation:{opacity:"show"},speed:"normal",autoArrows:true,dropShadows:false,disableHI:false,onInit:function(){},onBeforeShow:function(){},onShow:function(){},onHide:function(){}};
B.fn.extend({hideSuperfishUl:function(){var E=A.op,D=(E.retainPath===true)?E.$path:"";
E.retainPath=false;
var C=B(["li.",E.hoverClass].join(""),this).add(this).not(D).removeClass(E.hoverClass).find(">ul").hide().css("visibility","hidden");
E.onHide.call(C);
return this
},showSuperfishUl:function(){var E=A.op,D=A.c.shadowClass+"-off",C=this.addClass(E.hoverClass).find(">ul:hidden").css("visibility","visible");
A.IE7fix.call(C);
E.onBeforeShow.call(C);
C.animate(E.animation,E.speed,function(){A.IE7fix.call(C);
E.onShow.call(C)
});
return this
}})
})(jQuery);
/* http://mths.be/placeholder v2.0.7 by @mathias */
(function(G,I,D){var A="placeholder" in I.createElement("input"),E="placeholder" in I.createElement("textarea"),J=D.fn,C=D.valHooks,L,K;
if(A&&E){K=J.placeholder=function(){return this
};
K.input=K.textarea=true
}else{K=J.placeholder=function(){var M=this;
M.filter((A?"textarea":":input")+"[placeholder]").not(".placeholder").bind({"focus.placeholder":B,"blur.placeholder":F}).data("placeholder-enabled",true).trigger("blur.placeholder");
return M
};
K.input=A;
K.textarea=E;
L={get:function(N){var M=D(N);
return M.data("placeholder-enabled")&&M.hasClass("placeholder")?"":N.value
},set:function(N,O){var M=D(N);
if(!M.data("placeholder-enabled")){return N.value=O
}if(O==""){N.value=O;
if(N!=I.activeElement){F.call(N)
}}else{if(M.hasClass("placeholder")){B.call(N,true,O)||(N.value=O)
}else{N.value=O
}}return M
}};
A||(C.input=L);
E||(C.textarea=L);
D(function(){D(I).delegate("form","submit.placeholder",function(){var M=D(".placeholder",this).each(B);
setTimeout(function(){M.each(F)
},10)
})
});
D(G).bind("beforeunload.placeholder",function(){D(".placeholder").each(function(){this.value=""
})
})
}function H(N){var M={},O=/^jQuery\d+$/;
D.each(N.attributes,function(Q,P){if(P.specified&&!O.test(P.name)){M[P.name]=P.value
}});
return M
}function B(N,O){var M=this,P=D(M);
if(M.value==P.attr("placeholder")&&P.hasClass("placeholder")){if(P.data("placeholder-password")){P=P.hide().next().show().attr("id",P.removeAttr("id").data("placeholder-id"));
if(N===true){return P[0].value=O
}P.focus()
}else{M.value="";
P.removeClass("placeholder");
M==I.activeElement&&M.select()
}}}function F(){var R,M=this,Q=D(M),N=Q,P=this.id;
if(M.value==""){if(M.type=="password"){if(!Q.data("placeholder-textinput")){try{R=Q.clone().attr({type:"text"})
}catch(O){R=D("<input>").attr(D.extend(H(this),{type:"text"}))
}R.removeAttr("name").data({"placeholder-password":true,"placeholder-id":P}).bind("focus.placeholder",B);
Q.data({"placeholder-textinput":R,"placeholder-id":P}).before(R)
}Q=Q.removeAttr("id").hide().prev().attr("id",P).show()
}Q.addClass("placeholder");
Q[0].value=Q.attr("placeholder")
}else{Q.removeClass("placeholder")
}}}(this,document,jQuery));
if(typeof console==="undefined"||typeof console.log==="undefined"){console={log:function(){}}
}(function(A){A("ul.sf-menu").superfish({autoArrows:false,speed:"fast"});
A(".navtoggle").off().on("click",function(){A(this).toggleClass("nav-revealed");
A("nav>ul").slideToggle("fast")
});
A(".toggle-search-control").off().on("click",function(){A("header").toggleClass("reveal-search")
});
A("[name='search-scope']").change(function(){var C=A(this).val();
var B=A(".search-field [name='p']");
if(C=="site"){B.val(B.attr("data-value"))
}else{B.val("")
}});
A("[name='search-scope'][value='site']").change();
A(".mobile-toggle").on("click",function(D){D.preventDefault();
var C=A(this).parent().find("ul");
var B=A(this).find(".icon");
if(C.hasClass("revealed")){C.removeClass("revealed");
B.removeClass("icon-minus-sign");
B.addClass("icon-plus-sign")
}else{C.addClass("revealed");
B.removeClass("icon-plus-sign");
B.addClass("icon-minus-sign")
}});
A('meta[name="viewport"]').attr("content","width=device-width, initial-scale=1.0, minimum-scale=1.0, maximum-scale=5.0, user-scalable=yes");
A('input[type="search"]').placeholder();
A(window).on("storage",function(){A("link[rel='stylesheet']").each(function(B,C){var E=A(C);
var F="css:"+E.attr("href");
if(localStorage.hasOwnProperty(F)){A("[data-storage-key='"+F+"']").remove();
var D=A("<style data-storage-key='"+F+"'></style>").text(localStorage[F]);
E.after(D)
}})
})
})(jQuery);
(function(A){var G=window.matchMedia("(max-width: 768px)");
G.addListener(D);
D(G);
window.addEventListener("orientationchange",function(){var J=A("<div>").appendTo("body");
window.setTimeout(function(){J.remove()
},1)
});
function D(J){if(J.matches){F()
}else{H()
}}function F(){C();
A("nav>ul").hide();
var J=E().addClass("nav-toplevel").parent();
J.addClass("nav-item-expandable").children("a").on("click.clf-menu",function(K){K.stopPropagation();
K.preventDefault();
var L=A(this).parent();
L.toggleClass("nav-item-expanded").children("ul").first().slideToggle("fast")
});
J.filter(".active").children(".nav-toplevel").click();
A(".main-nav>ul").hide();
A(".main-nav>ul>li").not(".active").children("ul").hide()
}function H(){C();
A(".default-nav>ul>li").not(".active").children("ul").hide();
A(".nav-overview-item").hide();
var J=I();
J.hide();
var K=function(){J.stop(true,true).slideToggle()
};
A(".main-nav").hoverIntent({over:K,out:K,timeout:100})
}function C(){A("nav>ul").show().off("click","li");
A("nav>ul>li").show().off();
A(".nav-overview-item").show();
E().off();
E().parent().removeClass("nav-item-expanded").removeClass("nav-item-expandable");
A(".main-nav").show().off();
I().show().off()
}function E(){return A("nav>ul>li>a").filter(B)
}function I(){return A(".main-nav .sub-menu")
}function B(){return A(this).siblings("ul").length>0
}})(jQuery);
(function(C){C(".sub-menu").on("change",function(){var D=C(this).find(":selected").data("href");
if(D){window.location=D
}});
var B=C("#main h1").first();
var A=C(".mobile-sub-menu");
A.appendTo(B.parent())
})(jQuery);
if(typeof CQ=="undefined"||typeof CQ.WCM=="undefined"||typeof CQURLInfo=="undefined"||CQURLInfo.runModes!="author"||(CQ.WCM.getMode()!=null&&CQ.WCM.getMode()!="edit")){function moveToHashAnchor(){function B(G,H,F){return G>=H&&G<=F
}var E=window.location.hash+", [name='"+window.location.hash.substring(1)+"']";
var C=$(E).first();
if(C.length==0){return 
}var A=C.position().top;
var D=$(window).scrollTop();
if(!B(A,D-5,D+5)){$(window).scrollTop(A)
}}(function(A){A(document).ready(function(){A(".toggleContent").hide().click(function(B){B.stopPropagation()
});
A("div.toggle").click(function(){var C=A(this),D=this.className,B=D.match(/item\d+/)[0],E=A(".toggleContent."+B);
if(E.is(":visible")){E.slideUp(function(){C.css("background-position","0px 4px")
})
}else{C.css("background-position","-1786px 4px");
E.slideDown()
}});
if(A.browser.mozilla){moveToHashAnchor()
}})
})(jQuery)
}(function(E){E.fn.validateFields=function(){C()
};
var H=".field";
function G(){return E(H)
}function D(I){if(typeof I==="undefined"){I=G()
}I.find(".required-error-message, .constraint-error-message").hide()
}function B(I){I.removeClass("error");
D(I)
}var A="[name='spam-protection']";
function F(K){if(K.is(A)){return 
}var I=K.parents(H).first();
function J(){I.addClass("error")
}B(I);
if(K.attr("type")=="text"||K.prop("tagName").toLowerCase()=="textarea"||K.prop("tagName").toLowerCase()=="select"){if(K.is("[data-required]")){if(K.val().length==0){I.find(".required-error-message").show();
J();
return 
}}if(K.is("[data-constraint-type]")){E.getJSON("/bin/validator",{constraint:K.attr("data-constraint-type"),value:K.val()},function(M){if(!M.valid){J();
var L=I.find(".constraint-error-message");
if(L.text()==""){L.text(M.message)
}L.show()
}})
}}else{if(K.attr("type")=="checkbox"||K.attr("type")=="radio"){$checkedInputs=I.find("[type='checkbox'],[type='radio']").filter(":checked");
if($checkedInputs.length==0){I.find(".required-error-message").show();
J();
return 
}}}}function C(){G().find("input, textarea, select").not("[name='spam-protection']").blur(function(){F(E(this))
}).focus(function(){var I=E(this).parents(H).first();
B(I)
}).filter("[type='checkbox'],[type='radio']").click(function(){F(E(this))
}).end().filter("select").change(function(){F(E(this))
}).end().filter("[data-validate-on-load]").blur()
}E(document).ready(function(){var I=E(".spam-protection");
I.find("label").prepend('<input type="checkbox" name="spam-protection">');
I.show();
E("body").validateFields()
})
})(jQuery);
(function(A){var B=window.matchMedia("(min-width: 768px)");
A(".thickbox").fancybox({maxWidth:800,maxHeight:600,fitToView:false,width:"70%",height:"70%",autoSize:false,closeClick:false,openEffect:"none",closeEffect:"none",type:"iframe",beforeLoad:function(){if(!B.matches){window.location=A(this).attr("href");
return false
}}})
})(jQuery);
(function(A){window.RwdImageMap={originalCoordsAttrName:"data-original-coords",originalDimensionsAttr:"data-original-dimensions",init:function(){var B=this;
A("area").each(function(){var C=A(this);
C.attr(B.originalCoordsAttrName,C.attr("coords"))
});
A("img[usemap]").each(function(){var C=A(this);
var D=C[0].naturalWidth+"x"+C[0].naturalHeight;
C.attr(B.originalDimensionsAttr,D)
});
A(window).resize(function(){B.scaleCoords()
}).trigger("resize")
},scaleCoords:function(B){var C=this;
if(typeof B==="undefined"){B=A(".image ["+this.originalDimensionsAttr+"]")
}B.filter("["+this.originalDimensionsAttr+"]").each(function(){var E=A(this),F=E.attr(C.originalDimensionsAttr),H=E.width()/F.split("x")[0],G=E.height()/F.split("x")[1],D=E.attr("usemap").substring(1);
A("map[name='"+D+"']").find("area").each(function(){var L=A(this),K=L.attr(C.originalCoordsAttrName).split(","),I=[];
for(var J=0;
J<K.length;
J++){if(J%2===0){I.push(Math.round(K[J]*H))
}else{I.push(Math.round(K[J]*G))
}}L.attr("coords",I.join(","))
})
})
}};
A(document).ready(function(){RwdImageMap.init()
})
})(jQuery);
var renditionSizes=[{name:"xlarge",width:2000,height:2000},{name:"large",width:1280,height:1280},{name:"medium",width:640,height:640},{name:"small",width:320,height:320},{name:"tiny",width:96,height:96}];
function useRendition(A,B){A.each(function(){var D=$(this);
var C=D.attr("src").replace(/\.rendition-[a-zA-Z]+/,"");
var F=C.match(/\.[a-zA-Z]+$/)[0];
var E=C.replace(RegExp(F+"$"),".rendition-"+B+F);
D.attr("src",E);
RwdImageMap.scaleCoords(D)
})
}function orientedOnSide(){return typeof orientation!=="undefined"&&Math.abs(orientation)==90
}var devicePixelRatio=(typeof window.devicePixelRatio!=="undefined")?window.devicePixelRatio:1;
function defaultDimensionsObject(A){var B={naturalWidth:A[0].naturalWidth,naturalHeight:A[0].naturalHeight,requiredWidth:A.width()*devicePixelRatio,requiredHeight:A.height()*devicePixelRatio};
return B
}var dimensionCallbacks=[];
function registerDimensionsCallback(A){dimensionCallbacks.push(A)
}function carouselDimensions(B){var A=B.parents(".carousel").first();
if(A.length>0){return{naturalWidth:B[0].naturalWidth,naturalHeight:B[0].naturalHeight,requiredWidth:A.width()*devicePixelRatio,requiredHeight:A.height()*devicePixelRatio}
}else{return false
}}registerDimensionsCallback(carouselDimensions);
function dimensionsFor(A){var B=defaultDimensionsObject(A);
$.each(dimensionCallbacks,function(C,E){var D=E(A);
if(D){B=D
}});
return B
}function upscaleImagesUsingRequiredSized(){var B=/\.img\.[a-z]+\/\d+(\.rendition-[a-z])?\.[a-z]+/;
var A=$("img").filter(function(){return $(this).attr("src").match(B)
});
A.each(function(){var C=$(this);
var D=dimensionsFor(C);
if(D.naturalWidth<D.requiredWidth||D.naturalHeight<D.requiredHeight){upsizeToRequiredSize(C,D.requiredWidth,D.requiredHeight)
}})
}function upsizeToRequiredSize(C,A,B){var D=renditionSizes.sort(function(F,E){if(F.width>E.width){return 1
}else{if(F.width==E.width){return 0
}else{return -1
}}});
$.each(D,function(E,F){if(F.width>A||E==D.length-1){useRendition(C,F.name);
return false
}})
}function upscaleImagesUsingImageSizeMaps(){var B=screen.width;
var A=(window.devicePixelRatio!=="undefined")?window.devicePixelRatio:1;
if(orientedOnSide()){B=screen.height
}var C=B*A;
$.getJSON("/bin/image-size-maps.json",function(D){$.each(D,function(E,F){$.each(F.pixelWidthRenditionSizes,function(G,H){if(C>H.minWidth){useRendition($(F.selector),H.renditionSize);
return false
}})
})
})
}function upscaleImages(){upscaleImagesUsingRequiredSized()
}$(window).load(function(){upscaleImages();
$(window).bind("orientationchange",upscaleImages)
});
(function(B){var A=B("<div>").addClass("table");
B("#page-content table").wrap(A)
})(jQuery);
(function(B){var A=B(".externalvideo iframe, .video-slideshow iframe");
A.each(function(){B(this).data("aspectRatio",this.height/this.width).data("initialWidth",this.width).removeAttr("height").removeAttr("width")
});
B(window).resize(function(){A.each(function(){var D=B(this).data("autosize")?B(this).parent().width():B(this).data("initialWidth");
var C=Math.min(B(this).parent().width(),D);
B(this).width(C).height(C*B(this).data("aspectRatio"))
})
}).resize()
}(jQuery));
var VideoHandlers=new (function(){this.forFrame=function(B){var A=B.attr("src");
if(A.match(/vimeo\.com/)){return new VideoHandlers.Vimeo(B)
}else{if(A.match(/youtube\.com/)){return new VideoHandlers.YouTube(B)
}else{return new VideoHandlers.Unknown(B)
}}};
this.Unknown=function(B){var A=function(){}
};
this.Vimeo=function(A){this.self=this;
this.$iframe=A;
this.embedUrl=A.attr("src");
this.fromProvider=function(){return this.embedUrl.match(/vimeo\.com/)
};
this.extractVideoId=function(){var B=this.embedUrl.match(/video\/([^\?]+)/);
if(B){return B[1]
}else{return null
}};
this.populateDescription=function(B){var C=this.extractVideoId();
$.get("http://vimeo.com/api/v2/video/"+C+".json",function(F){var D=A.parents("li").first().find(".video-title").first();
var E=A.parents("li").first().find(".video-description").first();
if(A.data("show-title")){D.html(F[0].title)
}if(A.data("show-description")){E.html(F[0].description)
}$(window).resize()
})
}
};
this.YouTube=function(B){var A=this;
this.$iframe=B;
this.embedUrl=B.attr("src");
this.fromProvider=function(){return this.embedUrl.match(/youtube\.com/)
};
this.extractVideoId=function(){var C=this.embedUrl.match(/embed\/([^\?]+)/);
if(C){return C[1]
}else{return null
}};
this.populateDescription=function(){var C=this.extractVideoId();
$.get("https://gdata.youtube.com/feeds/api/videos/"+C+"?v=2",function(G){var D=$(G).find("title").first().text();
var F=$(G).find("description").first().text();
if(B.data("show-title")){B.parents("li").first().find(".video-title").first().html(D)
}if(B.data("show-description")){var E=A.formatDescription(F);
B.parents("li").first().find(".video-description").first().html(E)
}$(window).resize()
},"xml")
};
this.formatDescription=function(C){return C.replace(/\n/g,"<br>\n")
}
}
})();
$(document).ready(function(){if(!$().flexslider){return 
}$(".video-slideshow .flexslider").flexslider({animation:"slide",useCSS:false,animationLoop:false,smoothHeight:true,directionNav:false}).hover(function(){$(this).flexslider("pause")
});
$(".video-slideshow iframe").each(function(){var A=$(this);
VideoHandlers.forFrame(A).populateDescription()
}).load(function(){$(window).resize()
})
});