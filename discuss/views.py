from coredata.models import CourseOffering, Member
from courselib.auth import is_course_student_by_slug, is_course_staff_by_slug, ForbiddenResponse
from discuss.models import DiscussionTopic, DiscussionMessage, DiscussionSubscription
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from discuss.forms import discussion_topic_form_factory,\
    DiscussionTopicStatusForm, DiscussionMessageForm, DiscussionSubscriptionForm
import datetime, itertools, json
from . import activity

def _get_course_and_view(request, course_slug):
    """
    Validates the request and returns the course object and view perspective ('student', 'staff')
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    if not course.discussion():
        raise Http404
    if is_course_student_by_slug(request, course_slug):
        return course, 'student'
    elif is_course_staff_by_slug(request, course_slug):
        return course, 'staff'
    else:
        return HttpResponseForbidden(), None

def _get_member(username, discussion_view, course_slug):
    """
    Retrieves the Member object for a discussion topic/message
    """
    if discussion_view == 'student':
        return Member.objects.filter(offering__slug=course_slug, person__userid=username, role="STUD", offering__graded=True).exclude(offering__component="CAN")[0]
    elif discussion_view == 'staff':
        return Member.objects.filter(offering__slug=course_slug, person__userid=username, role__in=['INST', 'TA', 'APPR'], offering__graded=True).exclude(offering__component="CAN")[0]
    else:
        raise ValueError("Discussion view type must be either 'student' or 'staff'")


@login_required
def discussion_index(request, course_slug):
    """
    Index page to view all discussion topics
    """
    course, view = _get_course_and_view(request, course_slug)
    if view is None:
        # course is an HttpResponse in this case
        return course
    topics = DiscussionTopic.objects.filter(offering=course).order_by('-pinned', '-last_activity_at')
    activity.update_last_viewed(_get_member(request.user.username, view, course_slug))
    paginator = Paginator(topics, 10)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        topics = paginator.page(page)
    except (EmptyPage, InvalidPage):
        topics = paginator.page(paginator.num_pages)
    context = {'course': course, 'topics': topics, 'view': view, 'paginator': paginator, 'page': page}
    return render(request, 'discuss/index.html', context)
    

@login_required
def create_topic(request, course_slug):
    """
    Form to create a new discussion topic
    """
    course, view = _get_course_and_view(request, course_slug)
    if view is None:
        # course is an HttpResponse in this case
        return course
    if request.method == 'POST':
        form = discussion_topic_form_factory(view, data=request.POST)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.offering = course
            topic.author = _get_member(request.user.username, view, course_slug)
            topic.save()
            messages.add_message(request, messages.SUCCESS, 'Discussion topic created successfully.')
            return HttpResponseRedirect(reverse('offering:discussion:view_topic', kwargs={'course_slug': course_slug, 'topic_slug': topic.slug}))
    else:
        form = discussion_topic_form_factory(view)
    return render(request, 'discuss/create_topic.html', {'course': course, 'form': form})


@login_required()
def edit_topic(request, course_slug, topic_slug):
    """
    Form to edit a recently posted discussion topic (5 min window)
    """
    course, view = _get_course_and_view(request, course_slug)
    if view is None:
        # course is an HttpResponse in this case
        return course
    topic = get_object_or_404(DiscussionTopic, slug=topic_slug, offering=course)
    if topic.author.person.userid != request.user.username:
        return HttpResponseForbidden()
    if (datetime.datetime.now() - topic.created_at) > datetime.timedelta(minutes = 5):
        raise Http404
    
    if request.method == 'POST':
        form = discussion_topic_form_factory(view, data=request.POST, instance=topic)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Discussion topic edited successfully.')
            return HttpResponseRedirect(reverse('offering:discussion:view_topic', kwargs={'course_slug': course_slug, 'topic_slug': topic.slug}))
    else:
        form = discussion_topic_form_factory(view, instance=topic)
    
    return render(request, 'discuss/edit_topic.html', {'course': course, 'topic': topic, 'form': form})


@login_required
def view_topic(request, course_slug, topic_slug):
    """
    Page to view a discussion topic and reply
    """
    course, view = _get_course_and_view(request, course_slug)
    if view is None:
        # course is an HttpResponse in this case
        return course
    topic = get_object_or_404(DiscussionTopic, slug=topic_slug, offering=course)
    if view == 'student' and topic.status == 'HID':
        raise Http404
    replies = DiscussionMessage.objects.filter(topic=topic).order_by('created_at')
    
    if request.method == 'POST':
        if topic.status == 'CLO' and not view  == 'staff':
            raise Http404
        form = DiscussionMessageForm(data=request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.topic = topic
            message.author = _get_member(request.user.username, view, course_slug)
            message.save()
            messages.add_message(request, messages.SUCCESS, 'Sucessfully replied')
            return HttpResponseRedirect(reverse('offering:discussion:view_topic', kwargs={'course_slug': course_slug, 'topic_slug': topic.slug}))
    else:
        form = DiscussionMessageForm()
    context = {'course': course, 'topic': topic, 'replies': replies, 'view': view, 'form': form,
               'username': request.user.username}
    return render(request, 'discuss/topic.html', context)


@login_required
def change_topic_status(request, course_slug, topic_slug):
    """
    Form to change the status of a topic
    """
    course, view = _get_course_and_view(request, course_slug)
    if view is None:
        # course is an HttpResponse in this case
        return course
    topic = get_object_or_404(DiscussionTopic, slug=topic_slug, offering=course)
    if view != 'staff':
        return HttpResponseForbidden()
    if request.method == 'POST':
        form = DiscussionTopicStatusForm(request.POST, instance=topic)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Discussion topic has been successfully changed.')
            return HttpResponseRedirect(reverse('offering:discussion:view_topic', kwargs={'course_slug': course_slug, 'topic_slug': topic.slug}))
    else:
        form = DiscussionTopicStatusForm(instance=topic)
    return render(request, 'discuss/change_topic.html', {'course': course, 'topic': topic, 'form': form})



@login_required()
def edit_message(request, course_slug, topic_slug, message_slug):
    """
    Form to edit a recently posted reply (5 min window)
    """
    course, view = _get_course_and_view(request, course_slug)
    if view is None:
        # course is an HttpResponse in this case
        return course
    topic = get_object_or_404(DiscussionTopic, slug=topic_slug, offering=course)
    message = get_object_or_404(DiscussionMessage, slug=message_slug, topic=topic)
    if not message.author.person.userid == request.user.username:
        return HttpResponseForbidden
    if (datetime.datetime.now() - message.created_at) > datetime.timedelta(minutes = 5):
        raise Http404
    
    if request.method == 'POST':
        form = DiscussionMessageForm(data=request.POST, instance=message)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Reply successfully edited.')
            return HttpResponseRedirect(reverse('offering:discussion:view_topic', kwargs={'course_slug': course_slug, 'topic_slug': topic.slug}))
    else:
        form = DiscussionMessageForm(instance=message)
    return render(request, 'discuss/edit_reply.html', {'course':course, 'topic': topic, 'message': message, 'form': form})


@login_required
def remove_message(request, course_slug, topic_slug, message_slug):
    """
    POST to remove a topic message
    """
    course, view = _get_course_and_view(request, course_slug)
    if view is None:
        # course is an HttpResponse in this case
        return course
    if request.method != 'POST':
        raise Http404
    topic = get_object_or_404(DiscussionTopic, slug=topic_slug, offering=course)
    message = get_object_or_404(DiscussionMessage, slug=message_slug, topic=topic)
    if view == 'staff' or message.author.person.userid == request.user.username:
        message.status = 'HID'
        message.save()
        messages.add_message(request, messages.SUCCESS, 'Reply successfully removed.')
        return HttpResponseRedirect(reverse('offering:discussion:view_topic', kwargs={'course_slug': course_slug, 'topic_slug': topic_slug}))
    else:
        return HttpResponseForbidden()
    

@login_required()
def manage_discussion_subscription(request, course_slug):
    course, view = _get_course_and_view(request, course_slug)
    if view is None:
        # course is an HttpResponse in this case
        return course
    member = get_object_or_404(Member, offering=course, person__userid=request.user.username)
    sub, _ = DiscussionSubscription.objects.get_or_create(member=member)
    if request.method == 'POST':
        form = DiscussionSubscriptionForm(request.POST, instance=sub)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.member = member
            sub.save()
            messages.add_message(request, messages.SUCCESS, 'Updated your discussion subscription.')
            return HttpResponseRedirect(reverse('offering:discussion:discussion_index', kwargs={'course_slug': course_slug}))
        
    else:
        form = DiscussionSubscriptionForm(instance=sub)

    context = {'course':course, 'form': form}
    return render(request, 'discuss/manage_discussion_subscription.html', context)


@login_required
def download(request, course_slug):
    """
    Unlisted view to return all course discussion in JSON format.
    """
    course, view = _get_course_and_view(request, course_slug)
    if view != 'staff':
        return ForbiddenResponse(request)
    data = [t.to_dict() for t in DiscussionMessage.objects.filter(topic__offering=course)]
    return HttpResponse(json.dumps({"data": data}, indent=2), content_type='application/json')
