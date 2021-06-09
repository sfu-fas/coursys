from collections import Counter
from typing import Dict, List

from django import forms, template
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe

from coredata.models import Member
from dashboard.templatetags.form_display import required_message, label_display, field_display
from forum.models import Post, REACTION_CHOICES, REACTION_ICONS, Reaction, REACTION_SCORES, SCORE_STAFF_FACTOR, \
    REACTION_DESCRIPTIONS, Identity

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

    if reqcount > 0:
        out.append(required_message(None))

    out.append('<p><input class="submit" type="submit" value="%s" /></p>' % (escape(submit_verb),))

    return mark_safe('\n'.join(out))


@register.filter
def visible_author(post: Post, viewer: Member) -> str:
    return post.visible_author(viewer)


@register.filter
def editable_by(post: Post, viewer: Member) -> bool:
    return post.editable_by(viewer)


@register.simple_tag
def avatar_image(post: Post, viewer: Member, avatar_type=None) -> SafeString:
    # avatar_type argument used for the selection form, so user can preview.
    if not avatar_type:
        if post.sees_real_name(viewer):
            avatar_type = post.author_identity.avatar_type
        else:
            avatar_type = post.author_identity.anon_avatar_type

    url = post.author_identity.avatar_image_url(avatar_type=avatar_type, anon=not post.sees_real_name(viewer))
    return mark_safe(
        '<img src="' + escape(url) + '" alt="" class="avatar" loading="lazy" referrerpolicy="no-referrer" />')


@register.simple_tag
def reaction_display(post: Post, post_reactions: Dict[int, List[Reaction]], viewer_reactions: Dict[int, str]) -> SafeString:
    """
    Produce the display of reactions on this post
    """
    out = []
    reactions = post_reactions.get(post.id, [])
    viewer_reaction = viewer_reactions.get(post.id, 'NONE')

    score = sum(
        REACTION_SCORES[r.reaction] * (SCORE_STAFF_FACTOR if r.member.role in ['INST', 'TA'] else 1)
        for r in reactions
    )
    if not reactions:
        return mark_safe('<span class="reactions empty" data-score="%g"></span>' % (score,))

    out.append('<p class="reactions" data-score="%g">Reactions: ' % (score,))

    counts = [(n, reaction) for reaction, n in Counter(r.reaction for r in reactions).items()]
    counts.sort(key=lambda c: (-c[0], c[1]))  # decreasing frequency
    visible_counts = [
        '<span class="reaction %s" title="%s">%s&times;%i</span>'
        % ( 'active' if r==viewer_reaction else '', escape(REACTION_DESCRIPTIONS[r]), (REACTION_ICONS[r]), n)
        for n, r in counts
    ]
    out.extend(visible_counts)

    out.append('</p>')

    return mark_safe(''.join(out))


@register.simple_tag
def reaction_widget(post: Post, viewer: Member, viewer_reactions: Dict[int, str]) -> SafeString:
    """
    Produce the collection of links associated with "reacting" to a post.
    """
    if post.author_id == viewer.id:
        #return mark_safe('<p class="react-widget"><span class="empty">[cannot react to your own post]</span></p>')
        return mark_safe('')

    viewer_reaction = viewer_reactions.get(post.id, 'NONE')

    out = ['<p class="react-widget">React: ']
    for react, descr in REACTION_CHOICES:
        url = reverse(
            'offering:forum:react',
            kwargs={'course_slug': post.offering.slug, 'post_number': post.number, 'reaction': react}
        )
        cls = 'active' if viewer_reaction == react else ''
        html = '<a href="%s" title="%s" class="%s" data-target="main-panel">%s</a>\n' % (escape(url), escape(descr), cls, escape(REACTION_ICONS[react]))
        out.append(html)

    out.append('</p>')
    return mark_safe('\n'.join(out))

