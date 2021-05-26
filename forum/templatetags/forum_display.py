from collections import Counter
from typing import Dict, List

from django import forms, template
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe

from coredata.models import Member
from dashboard.templatetags.form_display import required_message, label_display, field_display
from forum.models import Post, REACTION_CHOICES, REACTION_ICONS, Reaction, REACTION_SCORES, SCORE_STAFF_FACTOR

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
def reaction_display(post: Post, post_reactions: Dict[int, List[Reaction]]) -> SafeString:
    """
    Produce the display of reactions on this post, given a dict of post.id -> [Reaction].
    """
    out = []
    if post.id in post_reactions:
        reactions = post_reactions[post.id]
    else:
        reactions = []

    score = sum(
        REACTION_SCORES[r.reaction] * (SCORE_STAFF_FACTOR if r.member.role in ['INST', 'TA'] else 1)
        for r in reactions
    )
    out.append('<div class="reactions" data-score="%g">' % (score,))

    counts = [(n, reaction) for reaction, n in Counter(r.reaction for r in reactions).items()]
    counts.sort(key=lambda c: (-c[0], c[1]))  # decreasing frequency
    visible_counts = ['<span class="reaction">%s&times;%i</span> ' % (escape(REACTION_ICONS[r]), n) for n, r in counts]
    out.extend(visible_counts)

    out.append('</div>')

    return mark_safe(''.join(out))


@register.filter
def reaction_widget(post: Post, viewer: Member) -> SafeString:
    """
    Produce the collection of links associated with "reacting" to a post.
    """
    if post.author_id == viewer.id:
        return ''

    out = []
    out.append('<p>React: ')
    for react, descr in REACTION_CHOICES:
        url = reverse(
            'offering:forum:react',
            kwargs={'course_slug': post.offering.slug, 'post_number': post.number, 'reaction': react}
        )
        html = '<a href="%s" title="react &ldquo;%s&rdquo; to this">%s</a>\n' % (escape(url), escape(descr), escape(REACTION_ICONS[react]))
        out.append(html)

    out.append('</p>')
    return mark_safe('\n'.join(out))

