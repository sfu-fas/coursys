from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect

from courselib.auth import requires_course_by_slug
from forum.forms import ThreadForm
from forum.models import Thread, AnonymousIdentity, Forum


@requires_course_by_slug
def index(request: HttpRequest, course_slug: str) -> HttpResponse:
    member = request.member
    offering = member.offering

    threads = Thread.objects.filter(post__offering=offering).select_related('post', 'post__author')

    context = {
        'offering': offering,
        'threads': threads,
    }
    return render(request, 'forum/index.html', context=context)


@requires_course_by_slug
def new_thread(request: HttpRequest, course_slug: str) -> HttpResponse:
    member = request.member
    offering = member.offering
    forum = Forum.for_offering(offering)

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