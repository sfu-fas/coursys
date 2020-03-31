import datetime
from collections import OrderedDict
from typing import Optional

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.generic import FormView
from django.views.generic.edit import ModelFormMixin, UpdateView

from coredata.models import CourseOffering
from courselib.auth import requires_course_by_slug, requires_course_staff_by_slug
from grades.models import Activity
from quizzes.forms import QuizForm, StudentForm
from quizzes.models import Quiz, QUESTION_TYPE_CHOICES, QUESTION_CLASSES, Question, QuestionAnswer


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
    else:
        raise Http404()


def _index_instructor(request: HttpRequest, offering: CourseOffering, activity: Activity, quiz: Quiz) -> HttpResponse:
    assert request.member.role in ['INST', 'TA']
    questions = Question.objects.filter(quiz=quiz)
    context = {
        'offering': offering,
        'activity': activity,
        'quiz': quiz,
        'questions': questions,
    }
    return render(request, 'quizzes/index_staff.html', context=context)


def _index_student(request: HttpRequest, offering: CourseOffering, activity: Activity, quiz: Quiz) -> HttpResponse:
    member = request.member
    assert member.role == 'STUD'

    questions = Question.objects.filter(quiz=quiz)
    question_lookup = {q.ident(): q for q in questions}
    question_number = {q.id: i + 1 for i, q in enumerate(questions)}

    fields = OrderedDict((q.ident(), q.entry_field(questionanswer=None)) for i, q in enumerate(questions))

    answers = list(QuestionAnswer.objects.filter(question__in=questions, student=member))
    answer_lookup = {a.question.ident(): a for a in answers}

    if request.method == 'POST':
        form = StudentForm(data=request.POST, files=request.FILES)
        form.fields = fields
        if form.is_valid():

            # Iterate through each answer we received, and create/update corresponding QuestionAnswer objects.
            for name, data in form.cleaned_data.items():
                try:
                    quest = question_lookup[name]
                except KeyError:
                    continue # Submitted a question that doesn't exist? Ignore

                n = question_number[quest.id]
                helper = quest.helper()
                answer = helper.to_jsonable(data)

                if name in answer_lookup:
                    # Have an existing QuestionAnswer: update only if answer has changed.
                    ans = answer_lookup[name]
                    if ans.answer == answer: # TODO: is == enough for all field data we might get?
                        messages.add_message(request, messages.INFO, 'Question #%i answer unchanged from previous submission.' % (n,))
                    else:
                        ans.modified_at = datetime.datetime.now()
                        ans.answer = answer
                        ans.save()
                        messages.add_message(request, messages.INFO, 'Question #%i answer saved.' % (n,))

                else:
                    # No existing QuestionAnswer: create one.
                    ans = QuestionAnswer(question=quest, student=member)
                    # keep answer_lookup up to date for filling form initial values below
                    answer_lookup[quest.ident()] = ans

                    ans.modified_at = datetime.datetime.now()
                    ans.answer = answer
                    ans.save()
                    messages.add_message(request, messages.INFO, 'Question #%i answer saved.' % (n,))

            messages.add_message(request, messages.SUCCESS, 'Quiz answers saved. You can continue to modify them, as long as you submit before the end of the quiz time.')
            return redirect('offering:quiz:index', course_slug=offering.slug, activity_slug=activity.slug)

    else:
        form = StudentForm()
        form.fields = fields

    question_data = list(zip(questions, form.visible_fields()))

    # fill form initial data with existing QuestionAnswer values
    for quest, field in question_data:
        if quest.ident() in answer_lookup:
            ans = answer_lookup[quest.ident()]
            quest.helper().fill_initial(field, ans)
        else:
            # No existing answer: let the field's original .initial persist
            pass

    context = {
        'offering': offering,
        'activity': activity,
        'quiz': quiz,
        'questions': questions,
        'question_data': question_data,
    }
    return render(request, 'quizzes/index_student.html', context=context)


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
        else:
            context['activity'] = get_object_or_404(Activity, slug=self.kwargs['activity_slug'],
                                                    offering__slug=self.kwargs['course_slug'])
            context['offering'] = context['activity'].offering

        return context


@requires_course_staff_by_slug
def question_edit(request: HttpRequest, course_slug: str, activity_slug: str) -> HttpResponse:
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering)
    quiz = get_object_or_404(Quiz, activity=activity)
    context = {
        'offering': offering,
        'activity': activity,
        'quiz': quiz,
    }

    if request.method == 'GET' and 'type' not in request.GET:
        # ask for type of question
        context['question_type_choices'] = QUESTION_TYPE_CHOICES
        return render(request, 'quizzes/question_type.html', context=context)

    # have type of question: deal with form
    qtype = request.GET['type']
    if qtype not in QUESTION_CLASSES:
        raise Http404()

    question = Question(quiz=quiz, type=qtype)
    question_helper = question.helper()

    if request.method == 'POST':
        form = question_helper.make_config_form(data=request.POST, files=request.FILES)
        if form.is_valid():
            question.config = form.to_jsonable()
            question.set_order()
            question.save()
            messages.add_message(request, messages.SUCCESS, 'Question added.')
            return redirect('offering:quiz:index', course_slug=course_slug, activity_slug=activity_slug)

    elif request.method == 'GET':
        form = question_helper.make_config_form()

    context['question_helper'] = question_helper
    context['form'] = form
    return render(request, 'quizzes/edit_question.html', context=context)

