from typing import Optional

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from courselib.auth import requires_course_by_slug
from forum.forms import ThreadForm
from forum.models import Thread, AnonymousIdentity, Forum


@requires_course_by_slug
def index(request: HttpRequest, course_slug: str, post_number : Optional[int] = None) -> HttpResponse:
    member = request.member
    offering = member.offering
    forum = Forum.for_offering_or_404(offering)

    threads = Thread.objects.filter(post__offering=offering).select_related('post', 'post__author', 'post__offering')

    if post_number is not None:
        current_thread = get_object_or_404(
            Thread.objects.select_related('post', 'post__author', 'post__offering'),
            post__offering=offering, post__number=post_number
        )
    else:
        current_thread = None

    context = {
        'offering': offering,
        'threads': threads,
        'post_number': post_number,
        'current_thread': current_thread,
    }
    return render(request, 'forum/index.html', context=context)


@requires_course_by_slug
def new_thread(request: HttpRequest, course_slug: str) -> HttpResponse:
    member = request.member
    offering = member.offering
    forum = Forum.for_offering_or_404(offering)

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
            return redirect('offering:forum:index', course_slug=offering.slug)

    else:
        form = ThreadForm(member=member, offering_identity=forum.identity)

    context = {
        'offering': offering,
        'form': form
    }
    return render(request, 'forum/new_thread.html', context=context)


@requires_course_by_slug
def view_thread(request: HttpRequest, course_slug: str, thread_slug: str) -> HttpResponse:
    member = request.member
    offering = member.offering
    forum = Forum.for_offering_or_404(offering)

    thread = get_object_or_404(Thread, post__offering=offering, slug=thread_slug)
    context = {
        'offering': offering,
        'thread': thread,
        'post': thread.post,
    }
    return render(request, 'forum/view_thread.html', context=context)
