from coredata.models import CourseOffering, Member
from courselib.auth import is_course_student_by_slug, is_course_staff_by_slug
from discuss.models import DiscussionTopic, DiscussionMessage, DiscussionSubscription, TopicSubscription
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from featureflags.flags import uses_feature
from discuss.forms import discussion_topic_form_factory,\
    DiscussionTopicStatusForm, DiscussionMessageForm, DiscussionSubscriptionForm, TopicSubscriptionForm
import datetime, itertools, json
import activity

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
    if discussion_view is 'student':
        return Member.objects.filter(offering__slug=course_slug, person__userid=username, role="STUD", offering__graded=True).exclude(offering__component="CAN")[0]
    elif discussion_view is 'staff':
        return Member.objects.filter(offering__slug=course_slug, person__userid=username, role__in=['INST', 'TA', 'APPR'], offering__graded=True).exclude(offering__component="CAN")[0]
    else:
        raise ValueError("Discussion view type must be either 'student' or 'staff'")

@uses_feature('discuss')
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
    return render(request, 'discuss/index.html', {'course': course, 'topics': topics, 'view': view})
    
@uses_feature('discuss')
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
        creole = DiscussionTopic(offering=course).get_creole()
        form = discussion_topic_form_factory(view, data=request.POST, creole=creole)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.offering = course
            topic.author = _get_member(request.user.username, view, course_slug)
            topic.save()
            messages.add_message(request, messages.SUCCESS, 'Discussion topic created successfully.')
            return HttpResponseRedirect(reverse('discuss.views.view_topic', kwargs={'course_slug': course_slug, 'topic_slug': topic.slug}))
    else:
        form = discussion_topic_form_factory(view, creole=None)
    return render(request, 'discuss/create_topic.html', {'course': course, 'form': form})

@uses_feature('discuss')
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
        creole = topic.get_creole()
        form = discussion_topic_form_factory(view, data=request.POST, creole=creole, instance=topic)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Discussion topic edited successfully.')
            return HttpResponseRedirect(reverse('discuss.views.view_topic', kwargs={'course_slug': course_slug, 'topic_slug': topic.slug}))
    else:
        form = discussion_topic_form_factory(view, creole=None, instance=topic)
    
    return render(request, 'discuss/edit_topic.html', {'course': course, 'topic': topic, 'form': form})

@uses_feature('discuss')
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

    # syntaxhighlighter brushes needed
    brushes = set(itertools.chain(topic.brushes(), *(r.brushes() for r in replies)))
    # who needs mathjax activated?
    need_mathjax = ['reply-content-%i' % (r.id) for r in replies if r.math()]
    if topic.math():
        need_mathjax.append('topic-content')
    any_math = bool(need_mathjax)
    need_mathjax = json.dumps(need_mathjax)
    
    if request.method == 'POST':
        if topic.status == 'CLO' and not view  == 'staff':
            raise Http404
        creole = topic.get_creole()
        form = DiscussionMessageForm(data=request.POST, creole=creole)
        if form.is_valid():
            message = form.save(commit=False)
            message.topic = topic
            message.author = _get_member(request.user.username, view, course_slug)
            message.save()
            messages.add_message(request, messages.SUCCESS, 'Sucessfully replied')
            return HttpResponseRedirect(reverse('discuss.views.view_topic', kwargs={'course_slug': course_slug, 'topic_slug': topic.slug}))
    else:
        form = DiscussionMessageForm(creole=None)
    context = {'course': course, 'topic': topic, 'replies': replies, 'view': view, 'form': form,
               'brushes': brushes, 'need_mathjax': need_mathjax, 'any_math': any_math}
    return render(request, 'discuss/topic.html', context)

@uses_feature('discuss')
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
    if view is not 'staff':
        return HttpResponseForbidden()
    if request.method == 'POST':
        form = DiscussionTopicStatusForm(request.POST, instance=topic)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Discussion topic has been successfully changed.')
            return HttpResponseRedirect(reverse('discuss.views.view_topic', kwargs={'course_slug': course_slug, 'topic_slug': topic.slug}))
    else:
        form = DiscussionTopicStatusForm(instance=topic)
    return render(request, 'discuss/change_topic.html', {'course': course, 'topic': topic, 'form': form})


@uses_feature('discuss')
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
        creole = topic.get_creole()
        form = DiscussionMessageForm(data=request.POST, instance=message, creole=creole)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Reply successfully edited.')
            return HttpResponseRedirect(reverse('discuss.views.view_topic', kwargs={'course_slug': course_slug, 'topic_slug': topic.slug}))
    else:
        form = DiscussionMessageForm(instance=message, creole=None)
    return render(request, 'discuss/edit_reply.html', {'course':course, 'topic': topic, 'message': message, 'form': form})

@uses_feature('discuss')
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
        return HttpResponseRedirect(reverse('discuss.views.view_topic', kwargs={'course_slug': course_slug, 'topic_slug': topic_slug}))
    else:
        return HttpResponseForbidden()
    
@uses_feature('discuss')
@login_required()
def manage_discussion_subscription(request, course_slug):
    course, _ = _get_course_and_view(request, course_slug)
    member = get_object_or_404(Member, offering=course, person__userid=request.user.username)
    sub, _ = DiscussionSubscription.objects.get_or_create(member=member)
    topic_subs = TopicSubscription.objects.filter(member=member, topic__offering=course) \
                 .exclude(status='NONE').select_related('topic')
    if request.method == 'POST':
        form = DiscussionSubscriptionForm(request.POST, instance=sub)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.member = member
            sub.save()
            messages.add_message(request, messages.SUCCESS, 'Updated your discussion subscription.')
            return HttpResponseRedirect(reverse('discuss.views.discussion_index', kwargs={'course_slug': course_slug}))
        
    else:
        form = DiscussionSubscriptionForm(instance=sub)

    context = {'course':course, 'form': form, 'topic_subs': topic_subs}
    return render(request, 'discuss/manage_discussion_subscription.html', context)

@uses_feature('discuss')
@login_required()
def manage_topic_subscription(request, course_slug, topic_slug):
    course, _ = _get_course_and_view(request, course_slug)
    member = get_object_or_404(Member, offering=course, person__userid=request.user.username)
    topic = get_object_or_404(DiscussionTopic, slug=topic_slug, offering=course)
    sub, _ = TopicSubscription.objects.get_or_create(member=member, topic=topic)
    if request.method == 'POST':
        form = TopicSubscriptionForm(request.POST, instance=sub)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.member = member
            sub.topic = topic
            sub.save()
            messages.add_message(request, messages.SUCCESS, 'Updated your subscription to "%s".' % (topic.title))
            return HttpResponseRedirect(reverse('discuss.views.view_topic', kwargs={'course_slug': course_slug, 'topic_slug': topic_slug}))
        
    else:
        form = TopicSubscriptionForm(instance=sub)

    context = {'course':course, 'topic': topic, 'form': form}
    return render(request, 'discuss/manage_topic_subscription.html', context)





