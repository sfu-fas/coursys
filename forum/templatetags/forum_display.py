from django import forms, template
from django.utils.safestring import SafeString, mark_safe

from coredata.models import Member
from dashboard.templatetags.form_display import required_message, label_display, field_display
from forum.models import Post

register = template.Library()


@register.filter
def forum_form(form: forms.Form, submit_verb='Submit', form_class='forum-form') -> SafeString:
    out = []
    # if the form has any widgets that have Media elements, include this
    out.append(str(form.media))
    out.append(str(form.non_field_errors()))

    if form.hidden_fields():
        out.append('<div style="display:none">')
        for field in form.hidden_fields():
            out.append(str(field))
        out.append('</div>')

    reqcount = 0
    out.append('<div class="%s">' % (form_class,))
    for field in form.visible_fields():
        if field.field.required:
            reqcount += 1

        out.append('<div class="form-field">')
        if field.label:
            out.append(label_display(field, form.prefix))
        out.append('</div>')

        #out.append('<dd>')
        out.append(field_display(field))
        #out.append('</dd>')
    out.append('</div>')

    if  reqcount > 0:
        out.append(required_message(None))

    out.append('<p><input class="submit" type="submit" value="%s" /></p>' % (submit_verb,))

    return mark_safe('\n'.join(out))


@register.filter
def visible_author(post: Post, viewer: Member) -> str:
    return post.visible_author(viewer)