from typing import Optional

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from courselib.auth import requires_course_by_slug
from forum.forms import ThreadForm, ReplyForm
from forum.models import Thread, AnonymousIdentity, Forum, Reply, IDENTITY_CHOICES
from forum.names_generator import get_random_name


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
                post.status = 'OPEN'
                thread = Thread(post=post, title=thread_form.cleaned_data['title'])
                thread.save()  # also saves the thread.post

                messages.add_message(request, messages.SUCCESS, 'Forum thread posted.')
                return redirect('offering:forum:view_thread', course_slug=offering.slug, post_number=post.number)

        else:
            thread_form = ThreadForm(member=member, offering_identity=forum.identity)

        context['thread_form'] = thread_form

    else:
        context['thread_form'] = None

    if post_number is not None:
        thread = get_object_or_404(
            Thread.objects.select_related('post', 'post__author', 'post__offering'),
            post__offering=offering, post__number=post_number
        )
    else:
        thread = None
    context['thread'] = thread
    context['post'] = thread.post if thread else None

    if view == 'view_thread':
        replies = Reply.objects.filter(thread=thread).select_related('post', 'post__author')

        # view_thread view has a form to reply to this thread
        if request.method == 'POST':
            reply_form = ReplyForm(data=request.POST, member=member, offering_identity=forum.identity)
            if reply_form.is_valid():
                rep_post = reply_form.save(commit=False)
                rep_post.offering = offering
                rep_post.author = member
                rep_post.status = 'OPEN'
                reply = Reply(post=rep_post, thread=thread, parent=thread.post)
                reply.save()  # also saves the reply.post
                return redirect('offering:forum:view_thread', course_slug=offering.slug, post_number=thread.post.number)
        else:
            reply_form = ReplyForm(member=member, offering_identity=forum.identity)

        context['reply_form'] = reply_form
        context['replies'] = replies
    else:
        context['reply_form'] = None
        context['replies'] = None

    threads = Thread.objects.filter(post__offering=offering).select_related('post', 'post__author', 'post__offering')
    context['threads'] = threads

    if fragment:
        # we have been asked for a page fragment: deliver only that.
        return render(request, 'forum/_'+view+'.html', context=context)

    return render(request, 'forum/index.html', context=context)


def index(request: HttpRequest, course_slug: str) -> HttpResponse:
    return _forum_omni_view(request, course_slug=course_slug, view='index')


def view_thread(request: HttpRequest, course_slug: str, post_number : Optional[int] = None) -> HttpResponse:
    return _forum_omni_view(request, course_slug=course_slug, view='view_thread', post_number=post_number)


def new_thread(request: HttpRequest, course_slug: str) -> HttpResponse:
    return _forum_omni_view(request, course_slug=course_slug, view='new_thread')


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
