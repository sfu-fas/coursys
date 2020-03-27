from typing import Optional

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.generic import FormView
from django.views.generic.edit import ModelFormMixin, UpdateView

from coredata.models import CourseOffering
from courselib.auth import requires_course_by_slug, requires_course_staff_by_slug
from grades.models import Activity
from quizzes.forms import QuizForm
from quizzes.models import Quiz


@requires_course_by_slug
def index(request: HttpRequest, course_slug: str, activity_slug: str) -> HttpResponse:
    role = request.member.role
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering)
    if role in ['INST', 'TA']:
        quiz = Quiz.objects.filter(activity=activity).first()  # will be None if no quiz created for this activity
        if not quiz:
            # no quiz created? Only option is to create.
            return redirect('offering:quiz:edit', course_slug=course_slug, activity_slug=activity_slug)
        return _index_instructor(request, offering, activity, quiz)
    elif role == 'STUD':
        quiz = get_object_or_404(Quiz, activity=activity)  # will 404 if no quiz created for this activity
        return _index_student(request, offering, activity, quiz)


def _index_instructor(request: HttpRequest, offering: CourseOffering, activity: Activity, quiz: Quiz) -> HttpResponse:
    context = {
        'offering': offering,
        'activity': activity,
        'quiz': quiz,
    }
    return render(request, 'quizzes/index_staff.html', context=context)


def _index_student(request: HttpRequest, offering: CourseOffering, activity: Activity, quiz: Quiz) -> HttpResponse:
    pass


@method_decorator(requires_course_staff_by_slug, name='dispatch')
class EditView(FormView, UpdateView, ModelFormMixin):
    model = Quiz
    form_class = QuizForm
    template_name = 'quizzes/edit.html'

    def get_object(self, queryset=None):
        activity = get_object_or_404(Activity, slug=self.kwargs['activity_slug'],
                                     offering__slug=self.kwargs['course_slug'])
        quiz = Quiz.objects.filter(activity=activity).first() # None if no Quiz created
        return quiz

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        activity = get_object_or_404(Activity, slug=self.kwargs['activity_slug'],
                                     offering__slug=self.kwargs['course_slug'])
        kwargs['activity'] = activity
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quiz'] = self.object
        if self.object:
            context['offering'] = self.object.activity.offering
            context['activity'] = self.object.activity
        return context

    def get_success_url(self):
        if hasattr(self, 'object'):
            url = self.object.get_absolute_url()
        else:
            url = ''
        return url
