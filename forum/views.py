import itertools
from typing import Optional, Dict, List

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect, Http404
from django.shortcuts import render, redirect, get_object_or_404

from courselib.auth import requires_course_by_slug
from forum.forms import ThreadForm, ReplyForm
from forum.models import Thread, AnonymousIdentity, Forum, Reply, IDENTITY_CHOICES, Reaction, Post, HaveRead, \
    APPROVAL_REACTIONS, REACTION_ICONS, APPROVAL_ROLES
from forum.names_generator import get_random_name


@transaction.atomic
@requires_course_by_slug
def _forum_omni_view(
        request: HttpRequest, *, course_slug: str, view: str,
        post_number : Optional[int] = None,
):
    """
    All of the main forum views (thread list + main panel) are handled server-side here.
    """
    member = request.member
    offering = member.offering
    forum = Forum.for_offering_or_404(offering)
    context = {
        'view': view,
        'offering': offering,
        'post_number': post_number,
        'viewer': member,
    }
    fragment = 'fragment' in request.GET

    if view == 'new_thread':
        if request.method == 'POST':
            thread_form = ThreadForm(data=request.POST, member=member, offering_identity=forum.identity)
            if thread_form.is_valid():
                post = thread_form.save(commit=False)
                post.offering = offering
                post.author = member
                post.update_status(commit=False)
                thread = Thread(post=post, title=thread_form.cleaned_data['title'])
                thread.save(create_history=True)  # also saves the thread.post

                # mark it as self-read
                HaveRead.objects.bulk_create([HaveRead(member=member, post_id=post.id)], ignore_conflicts=True)

                messages.add_message(request, messages.SUCCESS, 'Forum thread posted.')
                return redirect('offering:forum:view_thread', course_slug=offering.slug, post_number=post.number)

        else:
            thread_form = ThreadForm(member=member, offering_identity=forum.identity)

        context['thread_form'] = thread_form

    if view == 'view_thread':
        try:
            thread = get_object_or_404(
                Thread.objects.select_related('post', 'post__author', 'post__offering', 'post__author__person',
                                              'post__offering').filter_for(member),
                post__number=post_number
            )
        except Http404:
            # if we got a reply's number, redirect to its true location
            replies = list(Reply.objects.filter(post__number=post_number).filter_for(member)
                           .select_related('post', 'post__offering', 'thread'))
            if replies:
                return HttpResponsePermanentRedirect(replies[0].get_absolute_url())
            else:
                raise

        if member.role == 'STUD' and thread.visibility == 'INST':
            raise Http404

        context['post'] = thread.post
        context['thread'] = thread

        replies = Reply.objects.filter(thread=thread).filter_for(member) \
            .select_related('post', 'post__author', 'post__author__person', 'post__offering')

        # view_thread view has a form to reply to this thread
        if request.method == 'POST':
            reply_form = ReplyForm(data=request.POST, member=member, offering_identity=forum.identity)
            if reply_form.is_valid():
                rep_post = reply_form.save(commit=False)
                rep_post.offering = offering
                rep_post.author = member
                rep_post.type = 'DISC'
                rep_post.status = 'NOAN'
                reply = Reply(post=rep_post, thread=thread, parent=thread.post)
                reply.save(create_history=True)  # also saves the reply.post

                reply.thread.post.update_status(commit=True)

                # mark it as self-read
                HaveRead.objects.bulk_create([HaveRead(member=member, post_id=rep_post.id)], ignore_conflicts=True)

                return redirect('offering:forum:view_thread', course_slug=offering.slug, post_number=thread.post.number)
        else:
            reply_form = ReplyForm(member=member, offering_identity=forum.identity)

        # mark everything we're sending to the user as read
        HaveRead.objects.bulk_create(
            [HaveRead(member=member, post_id=thread.post_id)]
            + [HaveRead(member=member, post_id=r.post_id) for r in replies],
            ignore_conflicts=True
        )

        # collect all reactions for the thread: we can do it here in one query, not one for each reply later
        all_post_ids = [thread.post_id] + [r.post_id for r in replies]
        all_reactions = Reaction.objects.exclude(reaction='NONE').filter(post_id__in=all_post_ids).select_related('member').order_by('post')
        post_reactions: Dict[int, List[Reaction]] = {}
        for post_id, reactions in itertools.groupby(all_reactions, lambda r: r.post_id):
            post_reactions[post_id] = list(reactions)

        context['reply_form'] = reply_form
        context['replies'] = replies
        context['post_reactions'] = post_reactions

    threads = Thread.objects.filter_for(member) \
        .select_related('post', 'post__author', 'post__offering', 'post__author__person')
    context['threads'] = threads

    if view == 'summary':
        # Find threads with unread activity
        reads = HaveRead.objects.filter(member=member).values_list('post_id', flat=True)
        unread_post_ids = Post.objects.filter(offering=offering).exclude(id__in=reads).values_list('id', flat=True)
        # TODO: this creates three-level nested queries. Should we convert to a list here to simplify?
        #unread_post_ids = list(unread_post_ids)

        # we have all Post.id values that this user hasn't read. Now find corresponding Threads
        unread_threads = Thread.objects.filter(post_id__in=unread_post_ids).filter_for(member) \
            .select_related('post', 'post__author', 'post__offering')
        unread_replies = Reply.objects.filter(post_id__in=unread_post_ids).filter_for(member) \
            .select_related('thread', 'thread__post', 'thread__post__author', 'thread__post__offering')
        unread_threads = set(unread_threads) | set(r.thread for r in unread_replies)
        unread_threads = list(unread_threads)
        unread_threads.sort(key=Thread.sort_key)

        context['unread_threads'] = unread_threads

        # monkey-patch annotate each Thread so we know what's unread?
        #for t in unread_threads:
        #    t.contains_unread = t.id in unread_thread_ids

        if member.role in APPROVAL_ROLES:
            unanswered_threads = Thread.objects.filter(post__type='QUES', post__status='OPEN').filter_for(member) \
                .select_related('post', 'post__author', 'post__offering')

            approval_icons = ', '.join(REACTION_ICONS[r] for r in APPROVAL_REACTIONS)

            context['unanswered_threads'] = unanswered_threads
            context['approval_icons'] = approval_icons
            context['show_unanswered'] = True
        else:
            context['show_unanswered'] = False

    if fragment:
        # we have been asked for a page fragment: deliver only that.
        return render(request, 'forum/_'+view+'.html', context=context)

    else:
        # render the entire index page server-side
        return render(request, 'forum/index.html', context=context)


def summary(request: HttpRequest, course_slug: str) -> HttpResponse:
    return _forum_omni_view(request, course_slug=course_slug, view='summary')


def view_thread(request: HttpRequest, course_slug: str, post_number: int) -> HttpResponse:
    return _forum_omni_view(request, course_slug=course_slug, view='view_thread', post_number=post_number)


def new_thread(request: HttpRequest, course_slug: str) -> HttpResponse:
    return _forum_omni_view(request, course_slug=course_slug, view='new_thread')


@transaction.atomic
@requires_course_by_slug
def react(request: HttpRequest, course_slug: str, post_number: int, reaction: str) -> HttpResponse:
    member = request.member
    offering = member.offering
    forum = Forum.for_offering_or_404(offering)
    try:
        reply = get_object_or_404(Reply.objects.filter_for(member).select_related('post'), post__number=post_number)
        post = reply.post
    except Http404:
       thread = get_object_or_404(Thread.objects.filter_for(member).select_related('post'), post__number=post_number)
       post = thread.post

    if post.author_id != member.id:
        if Reaction.objects.filter(member=member, post=post).exists():
            Reaction.objects.filter(member=member, post=post).update(reaction=reaction)
        else:
            r = Reaction(member=member, post=post, reaction=reaction)
            r.save()

        if member.role in APPROVAL_ROLES:
            # update the .status of the parent post
            for r in Reply.objects.filter(post=post).select_related('parent'):
                r.parent.update_status(commit=True)

        messages.add_message(request, messages.SUCCESS, 'Reaction recorded.')

    return HttpResponseRedirect(post.get_absolute_url())


@requires_course_by_slug
def anon_identity(request: HttpRequest, course_slug: str) -> HttpResponse:
    member = request.member
    offering = member.offering
    forum = Forum.for_offering_or_404(offering)

    identity_description = dict(IDENTITY_CHOICES)[forum.identity]
    ident = AnonymousIdentity.for_member(member)
    sample_names = [get_random_name() for _ in range(10)]

    context = {
        'member': member,
        'offering': offering,
        'offering_identity_description': identity_description,
        'ident': ident,
        'sample_names': sample_names,
    }
    return render(request, 'forum/anon_identity.html', context=context)
