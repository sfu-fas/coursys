function ToggleFormContent(){if(!(this instanceof arguments.callee)){return new arguments.callee(arguments)
}var A=this;
A.effectDuration=0;
A.getSetClass=function(C){var B=C.attr("class").split(" ");
var D=null;
for(i=0;
i<B.length;
i++){if(B[i].match(/set-(.+)/)){D=B[i]
}}return D
};
A.selected=function(D){var C=D.attr("type");
var B=false;
if(C=="checkbox"||C=="radio"){B=D.attr("checked")
}else{B=true
}return B
};
A.toggleCheckboxTarget=function(C){var B=C.attr("name");
var D=A.getSetClass(C);
C.parents(".checkbox-group, .checkbox").find("[name='"+B+"']").each(function(){var F=jQuery(this);
var E=jQuery(".tfc-target."+F.val()+"."+D).parents("div.section");
if(F.is(":checked")){A.show(E)
}else{A.hide(E)
}})
};
A.toggleTarget=function(B){var C=A.getSetClass(B);
if(A.selected(B)&&B.val()!=""){A.hide(jQuery(".tfc-target."+C).parents("div.section"));
A.show(jQuery(".tfc-target."+B.val()+"."+C).parents("div.section"))
}};
A.hide=function(B,C){if(C==undefined){C=A.effectDuration
}B.hide()
};
A.show=function(B,C){if(C==undefined){C=A.effectDuration
}B.show()
};
A.init=function(){A.hide(jQuery(".tfc-target").parents("div.section"),0);
jQuery("input.tfc-trigger, select.tfc-trigger").change(function(){var B=jQuery(this);
var C=A.getSetClass(B);
if(C!=null){if(B.attr("type")=="checkbox"){A.toggleCheckboxTarget(B)
}else{A.toggleTarget(B)
}}else{if(C==null){throw"Cannot find a toggle form content set class on trigger."
}}}).change()
};
A.init()
}jQuery(document).ready(function(){ToggleFormContent()
});