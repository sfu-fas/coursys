import datetime
import functools
import itertools
from typing import Dict, List, Any

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect, Http404, \
    JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import cache_page
from haystack.query import SearchQuerySet

from coredata.models import Member, CourseOffering
from courselib.auth import user_passes_test, is_course_member_by_slug, ForbiddenResponse
from forum.forms import ThreadForm, ReplyForm, SearchForm, AvatarForm, InstrThreadForm, InstrReplyForm, DigestForm, \
    PseudonymForm, InstrEditReplyForm, InstrEditThreadForm
from forum.models import Thread, Identity, Forum, Reply, Reaction, \
    APPROVAL_REACTIONS, REACTION_ICONS, APPROVAL_ROLES, IDENTITY_CHOICES, ReadThread, ReadReply, Post, REGEN_MAX, \
    REGEN_POST_MAX
from forum.names_generator import get_random_name


THREAD_LIST_MAX = 100  # maximum number of threads to display in the thread list
# how long after Semester.end can TAs and student access the forum?
if settings.DEPLOY_MODE == 'production':
    ACCESS_AFTER_SEMESTER = datetime.timedelta(days=30)
else:
    ACCESS_AFTER_SEMESTER = datetime.timedelta(days=365)

APPROVAL_ICONS = ', '.join(REACTION_ICONS[r] for r in APPROVAL_REACTIONS)

# last_time = datetime.datetime.now()
# def _print_time(marker):
#     global last_time
#     now = datetime.datetime.now()
#     print(marker, now - last_time)
#     last_time = now


class ForumHttpRequest(HttpRequest):
    # subclass of HttpRequest that promises the fields the @forum_view decorator provides
    member: Member
    offering: CourseOffering
    forum: Forum
    fragment_request: bool


def forum_view(view):
    """
    Decorator for all forum views: ensures Forum.enabled, pre-fetches request.member and request.offering.
    """
    # is_course_member_by_slug sets request.member
    auth_decorator = user_passes_test(is_course_member_by_slug)

    @functools.wraps(view)
    def the_view(request: ForumHttpRequest, course_slug: str, **kwargs):
        with transaction.atomic():
            request.offering = request.member.offering
            request.forum = Forum.for_offering_or_404(request.offering)
            request.fragment_request = 'fragment' in request.GET
            # students and TAs are locked out of the forum reasonably-after the semester ends
            if request.member.role != 'INST':
                after_semester = datetime.date.today() - request.member.offering.semester.end
                if after_semester > ACCESS_AFTER_SEMESTER:
                    return ForbiddenResponse(request, errormsg='the forum is locked after the semester is over')
            response = view(request, **kwargs)
        return response

    return auth_decorator(the_view)


def _render_forum_page(request: ForumHttpRequest, context: Dict[str, Any]) -> HttpResponse:
    context['offering'] = request.offering
    context['viewer'] = request.member

    if request.fragment_request:
        # we have been asked for a page fragment: deliver only that.
        if context['view'] == 'summary':
            context.update(thread_list_context(request.member))
        resp = render(request, 'forum/_'+context['view']+'.html', context=context)
        # if thread_list_update, trigger a refresh of the thread_list view by the frontend
        thread_list_update = context.get('thread_list_update', False)
        assert context['view'] != 'thread_list' or not thread_list_update  # no infinite loops, please
        resp['X-update-thread-list'] = 'yes' if thread_list_update else 'no'
    else:
        # render the entire index page server-side
        context.update(thread_list_context(request.member))  # full pages include the thread list: fetch it
        resp = render(request, 'forum/index.html', context=context)

    return resp


def thread_list_context(member: Member) -> Dict[str, Any]:
    """
    Provide the context necessary to render a template with the thread list sidebar.
    """
    threads = Thread.objects.filter_for(member) \
        .select_related('post', 'post__author', 'post__offering', 'post__author__person', 'post__author_identity')

    read_thread_ids = ReadThread.objects.filter(member=member).values_list('thread_id', flat=True)
    unread_threads = threads.exclude(id__in=read_thread_ids)

    threads = threads[:THREAD_LIST_MAX]
    return {
        'threads': threads,
        'unread_threads': unread_threads,
    }


@forum_view
def summary(request: ForumHttpRequest) -> HttpResponse:
    context = {
        'view': 'summary',
    }
    search_form = SearchForm()
    context['search_form'] = search_form

    if request.member.role in APPROVAL_ROLES:
        unanswered_threads = Thread.objects.filter(post__type='QUES', post__status='OPEN').filter_for(request.member) \
            .select_related('post', 'post__author', 'post__offering', 'post__author__person', 'post__author_identity')

        context['unanswered_threads'] = unanswered_threads
        context['approval_icons'] = APPROVAL_ICONS
        context['show_unanswered'] = True
    else:
        context['show_unanswered'] = False

    return _render_forum_page(request, context)


@forum_view
def thread_list(request: ForumHttpRequest) -> HttpResponse:
    context = {
        'view': 'thread_list',
        'thread_list_update': False,
    }
    context.update(thread_list_context(request.member))
    return _render_forum_page(request, context)


@forum_view
def view_thread(request: ForumHttpRequest, post_number: int) -> HttpResponse:
    context = {
        'view': 'view_thread',
        'thread_list_update': False,
    }
    try:
        thread = get_object_or_404(
            Thread.objects.filter_for(request.member).select_related(
                'post', 'post__author', 'post__offering', 'post__author__person', 'post__offering',
                'post__author_identity__member__person'),
            post__number=post_number
        )
    except Http404:
        # if we got a reply's number, redirect to its true location
        replies = list(Reply.objects.filter(post__number=post_number).filter_for(request.member)
                       .select_related('post', 'post__offering', 'thread').order_by('post__created_at'))
        if replies:
            url = replies[0].get_absolute_url(fragment=request.fragment_request)
            return HttpResponsePermanentRedirect(url)
        else:
            raise

    context['post_number'] = post_number
    context['post'] = thread.post
    context['thread'] = thread

    replies = Reply.objects.filter(thread=thread).filter_for(request.member) \
        .select_related('post', 'post__author', 'post__author__person', 'post__offering',
                        'post__author_identity__member__person')

    can_mark_answered = request.member == thread.post.author \
                        and thread.post.editable_by(request.member) \
                        and thread.post.status == 'OPEN'
    context['can_mark_answered'] = can_mark_answered
    context['approval_icons'] = APPROVAL_ICONS

    if request.member.role in APPROVAL_ROLES:
        replyFormClass = InstrReplyForm
    else:
        replyFormClass = ReplyForm

    thread_locked = thread.post.status == 'LOCK' and request.member.role not in APPROVAL_ROLES
    context['thread_locked'] = thread_locked

    if can_mark_answered and request.method == 'POST' and 'answered' in request.POST:
        # the "mark as answered" button
        thread.post.marked_answered = True
        thread.post.update_status(commit=True)
        messages.add_message(request, messages.SUCCESS, 'Question marked as answered.')
        return redirect('offering:forum:view_thread', course_slug=request.offering.slug,
                        post_number=thread.post.number)

    elif request.method == 'POST':
        if thread_locked:
            reply_form = None
        else:
            # view_thread view has a form to reply to this thread
            reply_form = replyFormClass(data=request.POST, member=request.member, offering_identity=request.forum.identity)
            if reply_form.is_valid():
                rep_post = reply_form.save(commit=False)
                rep_post.offering = request.offering
                rep_post.author = request.member
                # for now at least: replies are not answer-requiring questions
                rep_post.type = 'DISC'
                rep_post.status = 'NOAN'
                reply = Reply(post=rep_post, thread=thread, parent=thread.post)
                reply.save(create_history=True, real_change=True)  # also saves the reply.post

                reply.thread.post.update_status(commit=True)

                # mark it as self-read
                ReadReply(member=request.member, reply_id=reply.id).save()

                return redirect('offering:forum:view_thread', course_slug=request.offering.slug,
                                post_number=thread.post.number)
    elif thread_locked:
        reply_form = None
    else:
        reply_form = replyFormClass(member=request.member, offering_identity=request.forum.identity)

    # mark everything we're sending to the user as read
    ReadThread.objects.bulk_create(
        [ReadThread(member=request.member, thread_id=thread.id)],
        ignore_conflicts=True
    )
    ReadReply.objects.bulk_create(
        [ReadReply(member=request.member, reply_id=r.id) for r in replies],
        ignore_conflicts=True
    )
    context['thread_list_update'] = True

    # collect all reactions for the thread: we can do it here in one query, not one for each reply later
    all_post_ids = [thread.post_id] + [r.post_id for r in replies]
    all_reactions = Reaction.objects.exclude(reaction='NONE').filter(post_id__in=all_post_ids).select_related(
        'member').order_by('post')
    post_reactions: Dict[int, List[Reaction]] = {}
    for post_id, reactions in itertools.groupby(all_reactions, lambda r: r.post_id):
        post_reactions[post_id] = list(reactions)

    # ... and the viewer's reactions
    viewer_reactions = Reaction.objects.exclude(reaction='NONE').filter(post_id__in=all_post_ids, member=request.member)
    viewer_reactions = {r.post_id: r.reaction for r in viewer_reactions}

    context['reply_form'] = reply_form
    context['replies'] = replies
    context['post_reactions'] = post_reactions
    context['viewer_reactions'] = viewer_reactions
    context['instr_editing'] = request.member.role in APPROVAL_ROLES

    return _render_forum_page(request, context)


@forum_view
def new_thread(request: ForumHttpRequest) -> HttpResponse:
    context = {
        'view': 'new_thread',
    }
    if request.member.role in APPROVAL_ROLES:
        threadFormClass = InstrThreadForm
    else:
        threadFormClass = ThreadForm

    if request.method == 'POST':
        thread_form = threadFormClass(data=request.POST, member=request.member, offering_identity=request.forum.identity)
        if thread_form.is_valid():
            post = thread_form.save(commit=False)
            post.offering = request.offering
            post.author = request.member
            post.update_status(commit=False)
            thread = Thread(post=post, title=thread_form.cleaned_data['title'],
                            privacy=thread_form.cleaned_data['privacy'])

            # record broadcast_announcement logic (actual broadcast action handled below)
            thread.was_broadcast = ('broadcast_announcement' in thread_form.cleaned_data
                    and thread_form.cleaned_data['broadcast_announcement']
                    and request.member.role in APPROVAL_ROLES)
            # also pin if it's an announcement
            thread.pin = 1 if thread.was_broadcast else 0

            thread.save(create_history=True, real_change=True)  # also saves the thread.post

            if thread.was_broadcast:
                if False and settings.USE_CELERY:
                    from .tasks import broadcast_announcement
                    broadcast_announcement.delay(thread.id)
                else:
                    thread.broadcast_announcement()

            # mark it as self-read
            ReadThread(member=request.member, thread_id=thread.id).save()

            messages.add_message(request, messages.SUCCESS, 'Forum thread posted.')
            return redirect('offering:forum:view_thread', course_slug=request.offering.slug, post_number=post.number)

    else:
        thread_form = threadFormClass(member=request.member, offering_identity=request.forum.identity)

    context['thread_form'] = thread_form
    return _render_forum_page(request, context)


@forum_view
def edit_post(request: ForumHttpRequest, post_number: int) -> HttpResponse:
    try:
        thread = get_object_or_404(
            Thread.objects.select_related('post', 'post__author', 'post__offering', 'post__author__person',
                                          'post__offering', 'post__author_identity__member__person').filter_for(request.member),
            post__number=post_number
        )
        post = thread.post
        reply = None
        header_thread = None
        thread_locked = thread.post.status == 'LOCK' and request.member.role not in APPROVAL_ROLES
        if thread_locked:
            return ForbiddenResponse(request, errormsg='Posts cannot be edited because this thread is locked')

        if post.author == request.member:
            Form = ThreadForm
        else:
            Form = InstrEditThreadForm
    except Http404:
        # if we got a reply's number, deal with that
        replies = list(Reply.objects.filter(post__number=post_number).filter_for(request.member)
                       .select_related('post', 'post__offering', 'thread__post'))
        if replies:
            reply = replies[0]
            post = reply.post
            thread = None
            header_thread = reply.thread
            thread_locked = header_thread.post.status == 'LOCK' and request.member.role not in APPROVAL_ROLES
            if thread_locked:
                return ForbiddenResponse(request, errormsg='Posts cannot be edited because this thread is locked')

            if post.author == request.member:
                Form = ReplyForm
            else:
                Form = InstrEditReplyForm
        else:
            raise

    if not post.editable_by(request.member):
        raise Http404()

    if request.method == 'POST':
        form = Form(instance=post, data=request.POST, member=request.member, offering_identity=request.forum.identity)
        if form.is_valid():
            post = form.save(commit=False)
            post.offering = request.offering
            post.update_status(commit=False)
            if thread:
                thread.title = form.cleaned_data['title']
                thread.privacy = form.cleaned_data['privacy']
                thread.save(create_history=True, real_change=True)  # also saves the thread.post
                # mark it as self-read
                ReadThread.objects.bulk_create([ReadThread(member=request.member, thread_id=thread.id)], ignore_conflicts=True)
            else:
                reply.save(create_history=True, real_change=True)  # also saves the reply.post
                # mark it as self-read
                ReadReply.objects.bulk_create([ReadReply(member=request.member, reply_id=reply.id)], ignore_conflicts=True)

            messages.add_message(request, messages.SUCCESS, 'Post updated.')
            return redirect('offering:forum:view_thread', course_slug=request.offering.slug, post_number=post.number)

    else:
        if thread:
            form = Form(instance=post, offering_identity=request.forum.identity, member=request.member,
                                     initial={'title': thread.title, 'privacy': thread.privacy})
        else:
            form = Form(instance=post, offering_identity=request.forum.identity, member=request.member)

    context = {
        'view': 'edit_post',
        'member': request.member,
        'offering': request.offering,
        'post': post,
        'header_thread': header_thread,
        'form': form,
    }
    return _render_forum_page(request, context)


@cache_page(3600)
@forum_view
def preview(request: ForumHttpRequest) -> JsonResponse:
    from courselib.markup import markup_to_html
    try:
        html = markup_to_html(request.GET['content'], request.GET['markup'], math=request.GET['math'] == 'true', restricted=True, forum_links=True)
        return JsonResponse({'html': html})
    except:  # yes I'm catching anything: any failure is low-consequence, so let it go.
        return JsonResponse({'html': ''})


@forum_view
def react(request: ForumHttpRequest, post_number: int, reaction: str) -> HttpResponse:
    try:
        reply = get_object_or_404(Reply.objects.filter_for(request.member).select_related('post', 'thread__post'), post__number=post_number)
        post = reply.post
        locked = reply.thread.post.status == 'LOCK'
    except Http404:
        thread = get_object_or_404(Thread.objects.filter_for(request.member).select_related('post'), post__number=post_number)
        post = thread.post
        locked = thread.post.status == 'LOCK'

    if post.author_id != request.member.id and not locked:
        if Reaction.objects.filter(member=request.member, post=post).exists():
            Reaction.objects.filter(member=request.member, post=post).update(reaction=reaction)
        else:
            r = Reaction(member=request.member, post=post, reaction=reaction)
            r.save()

        # update the .status of the parent post
        for r in Reply.objects.filter(post=post).select_related('parent'):
            r.parent.update_status(commit=True)

        if not request.fragment_request:
            messages.add_message(request, messages.SUCCESS, 'Reaction recorded.')

    if request.fragment_request:
        return HttpResponseRedirect(post.get_absolute_url() + '?fragment=yes')
    else:
        return HttpResponseRedirect(post.get_absolute_url())


@forum_view
def pin(request: ForumHttpRequest, post_number: int) -> HttpResponse:
    if request.member.role not in APPROVAL_ROLES:
        raise Http404

    thread = get_object_or_404(Thread.objects.filter_for(request.member).select_related('post'), post__number=post_number)

    pin = 'pin' in request.GET
    thread.pin = 1 if pin else 0
    thread.save(real_change=False)
    if not request.fragment_request:
        if pin:
            messages.add_message(request, messages.SUCCESS, 'Thread pinned.')
        else:
            messages.add_message(request, messages.SUCCESS, 'Thread unpinned.')

    if request.fragment_request:
        return HttpResponseRedirect(thread.get_absolute_url() + '?fragment=yes')
    else:
        return HttpResponseRedirect(thread.get_absolute_url())


@forum_view
def lock(request: ForumHttpRequest, post_number: int) -> HttpResponse:
    if request.member.role not in APPROVAL_ROLES:
        raise Http404

    thread = get_object_or_404(Thread.objects.filter_for(request.member).select_related('post'), post__number=post_number)

    lock = 'lock' in request.GET
    if lock:
        thread.post.status = 'LOCK'
    else:
        thread.post.status = ''
        thread.post.update_status(commit=False)
    thread.post.save(real_change=False)

    if not request.fragment_request:
        if lock:
            messages.add_message(request, messages.SUCCESS, 'Thread locked.')
        else:
            messages.add_message(request, messages.SUCCESS, 'Thread unlocked.')

    if request.fragment_request:
        return HttpResponseRedirect(thread.get_absolute_url() + '?fragment=yes')
    else:
        return HttpResponseRedirect(thread.get_absolute_url())


@forum_view
def identity(request: ForumHttpRequest) -> HttpResponse:
    identity_description = dict(IDENTITY_CHOICES)[request.forum.identity]
    ident = Identity.for_member(request.member)
    sample_names = [get_random_name() for _ in range(6)]

    if request.method == 'POST' and request.POST.get('form', '') == 'avatar':
        avatar_form = AvatarForm(identity=ident, data=request.POST)
        if avatar_form.is_valid():
            ident.avatar_type = avatar_form.cleaned_data['avatar_type']
            ident.anon_avatar_type = avatar_form.cleaned_data['anon_avatar_type']
            ident.save()
            messages.add_message(request, messages.SUCCESS, 'Avatar updated.')
            return redirect('offering:forum:identity', course_slug=request.offering.slug)
    else:
        avatar_form = AvatarForm(identity=ident)

    posts_made = Post.objects.filter(author=request.member).exclude(status='HIDD').count()
    regen_remaining = REGEN_MAX - ident.regen_count
    can_regen = posts_made <= REGEN_POST_MAX and regen_remaining > 0

    if request.method == 'POST' and request.POST.get('form', '') == 'pseudonym':
        pseudonym_form = PseudonymForm(data=request.POST)
        if pseudonym_form.is_valid() and can_regen and request.member.role == 'STUD':
            ident.regenerate(save=True)
            messages.add_message(request, messages.SUCCESS, 'Pseudonym regenerated: %s.' % (ident.pseudonym,))
            return redirect('offering:forum:identity', course_slug=request.offering.slug)
    else:
        pseudonym_form = PseudonymForm()

    context = {
        'view': 'identity',
        'member': request.member,
        'offering': request.offering,
        'offering_identity_description': identity_description,
        'ident': ident,
        'sample_names': sample_names,
        'posts_made': posts_made,
        'regen_remaining': regen_remaining,
        'REGEN_MAX': REGEN_MAX,
        'REGEN_POST_MAX': REGEN_POST_MAX,
        'can_regen': can_regen,
        'avatar_form': avatar_form,
        'pseudonym_form': pseudonym_form,
    }
    return _render_forum_page(request, context)


@forum_view
def digest(request: ForumHttpRequest) -> HttpResponse:
    ident = Identity.for_member(request.member)
    if request.method == 'POST':
        form = DigestForm(data=request.POST)
        if form.is_valid():
            ident.digest_frequency = form.cleaned_data['digest_frequency']
            if ident.digest_frequency in [0, '0']:
                ident.digest_frequency = None
            ident.save()
            messages.add_message(request, messages.SUCCESS, 'Digest setting updated.')
            return redirect('offering:forum:digest', course_slug=request.offering.slug)
    else:
        form = DigestForm(initial={'digest_frequency': ident.digest_frequency if ident.digest_frequency else 0})
    context = {
        'view': 'digest',
        'form': form,
    }
    return _render_forum_page(request, context)


@forum_view
def search(request: ForumHttpRequest) -> HttpResponse:
    search_form = SearchForm(request.GET)
    if search_form.is_valid():
        q = search_form.cleaned_data['q']
        results = SearchQuerySet().models(Thread).filter(offering_slug=request.offering.slug).exclude(status='HIDD')
        # enforce privacy here: no analogue of .filter_for on the SearchQuerySet
        if request.member.role == 'STUD':
            results = results.filter(privacy='ALL')

        results = results.filter(text__fuzzy=q)
        results = list(results)
        results.sort(key=lambda r: -r.score)
        results = results[:THREAD_LIST_MAX]
    else:
        results = []

    context = {
        'view': 'search',
        'member': request.member,
        'offering': request.offering,
        'search_form': search_form,
        'results': results,
    }
    return _render_forum_page(request, context)


@forum_view
def dump(request: ForumHttpRequest) -> JsonResponse:
    if request.member.role not in ['INST', 'TA']:
        return JsonResponse({})

    reactions = Reaction.objects.filter(post__offering=request.offering).select_related('member').order_by('post_id')
    reaction_data = {post_id: list(rs) for post_id, rs in itertools.groupby(reactions, lambda r: r.post_id)}

    threads = Thread.objects.filter_for(request.member).select_related('post', 'post__author__person', 'post__author_identity').order_by('post__number')
    thread_data = {t.id: t.as_json(request.member, reaction_data=reaction_data) for t in threads}

    replies = Reply.objects.filter_for(request.member).select_related('post', 'post__author__person', 'post__author_identity').order_by('post__number')
    for r in replies:
        rs = thread_data[r.thread_id]['replies']
        rs.append(r.as_json(request.member, reaction_data=reaction_data))

    data = {
        'threads': list(thread_data.values()),
    }
    response = JsonResponse(data)
    response['Content-Disposition'] = 'inline; filename="forum-%s.json"' % (request.offering.slug,)
    return response


@forum_view
def debug_digest(request: ForumHttpRequest) -> HttpResponse:
    from forum.tasks import digest_content
    identity = Identity.for_member(request.member)
    html = digest_content(identity)
    return HttpResponse(html)