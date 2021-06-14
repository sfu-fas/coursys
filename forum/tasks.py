import datetime
import itertools
from typing import Optional, List, Tuple

from celery.schedules import crontab
from django import template
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.urls import reverse
from django.utils.safestring import SafeString

from courselib.celerytasks import task, periodic_task
from forum.models import Identity, Reply, ReadReply, Thread, ReadThread
from forum.views import thread_list_context, ACCESS_AFTER_SEMESTER


epsilon = datetime.timedelta(minutes=5)


def digest_content(ident: Identity) -> Optional[SafeString]:
    """
    Generate the HTML content of the digest email for this user. Returns None if no recent activity.
    """
    threads = Thread.objects.filter_for(ident.member) \
        .select_related('post', 'post__offering', 'post__author_identity', 'post__author__person')
    read_thread_ids = ReadThread.objects.filter(member=ident.member).values_list('thread_id', flat=True)
    unread_threads = threads.exclude(id__in=read_thread_ids)

    unread_threads = unread_threads.filter(last_activity__gte=ident.last_digest)
    thread_map = {t.id: t for t in unread_threads}

    read_replies = ReadReply.objects.filter(member=ident.member).values_list('reply_id', flat=True)
    unread_replies = Reply.objects.filter(thread__in=unread_threads).exclude(id__in=read_replies) \
        .select_related('post', 'post__offering', 'post__author_identity__member__person', 'post__author__person')
    unread_replies = unread_replies.filter(post__modified_at__gte=ident.last_digest)

    # collect all threads with unread activity, and corresponding replies
    activity: List[Tuple[Thread, List[Reply]]] = []
    found_thread_ids = set()
    for thread_id, replies in itertools.groupby(unread_replies, lambda r: r.thread_id):
        activity.append((thread_map[thread_id], list(replies)))
        found_thread_ids.add(thread_id)

    for t in unread_threads:
        # find threads where the thread is newly started/edited (but no replies)
        if t.id in found_thread_ids:
            continue
        activity.append((t, []))

    activity.sort(key=lambda pair: pair[0].last_activity)

    if not activity:
        return None

    templ = template.loader.get_template('forum/digest_email.html')
    context = {
        'BASE_ABS_URL': settings.BASE_ABS_URL,
        'offering': ident.offering,
        'activity': activity,
    }
    html = templ.render(context, None)

    return html


@task(queue='batch')
def send_digest(ident_id: int) -> None:
    """
    Send digest of any new forum activity to this user (and update their .last_digest).

    Note: doesn't really care what their .digest_frequency is: sends any activity since their .last_digest.
    """
    with transaction.atomic():
        ident = Identity.objects.select_related('offering', 'member__person').get(id=ident_id)
        html = digest_content(ident)
        ident.last_digest = datetime.datetime.now()
        ident.save()
        if not html:
            # no activity to report
            return

        plain = 'There is new activity in the %s %s %s discussion forum: %s%s' \
                % (ident.offering.subject, ident.offering.number, ident.offering.section,
                   settings.BASE_ABS_URL, reverse('offering:forum:summary', kwargs={'course_slug': ident.offering.slug}))
        email = EmailMultiAlternatives(
            subject='%s %s %s forum activity digest' % (ident.offering.subject, ident.offering.number, ident.offering.section),
            body=plain,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[ident.member.person.full_email()],
        )
        email.attach_alternative(html, "text/html")
        email.send(fail_silently=False)


@periodic_task(run_every=crontab(hour='*'))
def send_digests() -> None:
    now = datetime.datetime.now()
    idents = Identity.objects.filter(
        member__offering__semester__start__lt=now,
        member__offering__semester__end__gt=now - ACCESS_AFTER_SEMESTER,
        digest_frequency__isnull=False,
    ).select_related('offering', 'member', 'member__person')

    for i in idents:
        # whose digest is actually due?
        if i.last_digest < now - datetime.timedelta(hours=i.digest_frequency):
            send_digest.delay(i.id)
