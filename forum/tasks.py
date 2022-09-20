import datetime
import itertools
import time
from typing import Optional, List, Tuple

from django import template
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import QuerySet
from django.urls import reverse
from django.utils.safestring import SafeString

from coredata.models import Member, Semester
from courselib.celerytasks import task
from forum.models import Identity, Reply, ReadReply, Thread, ReadThread, APPROVAL_ROLES
from forum.views import ACCESS_AFTER_SEMESTER


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
        # Exclude broadcasted threads, since they have already been pushed by email.
        if t.was_broadcast:
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
            headers={'X-coursys-topic': 'forum', 'X-course': ident.offering.slug},
        )
        email.attach_alternative(html, 'text/html')
        email.send(fail_silently=False)


def _relevant_semester_ids() -> List[int]:
    now = datetime.datetime.now()
    semester_ids = list(
        Semester.objects.filter(start__lt=now, end__gt=now - ACCESS_AFTER_SEMESTER).values_list('id', flat=True)
    )
    return semester_ids


def _relevant_idents() -> QuerySet:
    idents = Identity.objects.filter(
        member__offering__semester_id__in=_relevant_semester_ids()
    ).exclude(member__role='DROP').select_related('offering', 'member', 'member__person')
    return idents


@task(queue='batch')
def create_instr_idents() -> None:
    """
    Find instructors/TAs without identity objects: create Identity objects for them so they have INSTR_DEFAULT_FREQUENCY.
    """
    idents = _relevant_idents().filter(member__role__in=APPROVAL_ROLES)
    ident_members = list(idents.values_list('member__id', flat=True))
    members_without = Member.objects.filter(
        role__in=APPROVAL_ROLES,
        offering__semester_id__in=_relevant_semester_ids(),
    ).exclude(id__in=ident_members).select_related('offering')

    with transaction.atomic():
        for m in members_without:
            Identity.new(offering=m.offering, member=m, save=True)


@task()
def send_digests(immediate=False) -> None:
    now = datetime.datetime.now()
    idents = _relevant_idents().filter(digest_frequency__isnull=False)
    for i in idents:
        # whose digest is actually due?
        if i.last_digest < now - datetime.timedelta(hours=i.digest_frequency):
            if immediate:
                # send now, without celery tasks
                send_digest.apply(args=[i.id])
            else:
                send_digest.delay(i.id)

    # create any missing Identity objects, so we pick them up on the next run.
    if immediate:
        create_instr_idents.apply()
    else:
        create_instr_idents.delay()


@task(queue='batch')
def broadcast_announcement(thread_id: int) -> None:
    try:
        thread = Thread.objects.get(id=thread_id)
    except Thread.DoesNotExist:
        time.sleep(5)  # give the view a chance to commit its transaction
        thread = Thread.objects.get(id=thread_id)
    thread.broadcast_announcement()