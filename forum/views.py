from typing import Optional

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from courselib.auth import requires_course_by_slug
from forum.forms import ThreadForm
from forum.models import Thread, AnonymousIdentity, Forum


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
    }
    fragment = 'fragment' in request.GET

    if view == 'new_thread':
        if request.method == 'POST':
            form = ThreadForm(data=request.POST, member=member, offering_identity=forum.identity)
            if form.is_valid():
                post = form.save(commit=False)
                post.offering = offering
                post.author = member
                post.status = 'OPEN'
                thread = Thread(post=post, title=form.cleaned_data['title'])
                thread.save()  # also saves the thread.post

                messages.add_message(request, messages.SUCCESS, 'Forum thread posted.')
                return redirect('offering:forum:view_thread', course_slug=offering.slug, post_number=post.number)

        else:
            form = ThreadForm(member=member, offering_identity=forum.identity)

        context['form'] = form

    else:
        context['form'] = None

    if post_number is not None:
        thread = get_object_or_404(
            Thread.objects.select_related('post', 'post__author', 'post__offering'),
            post__offering=offering, post__number=post_number
        )
    else:
        thread = None
    context['thread'] = thread
    context['post'] = thread.post if thread else None

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
