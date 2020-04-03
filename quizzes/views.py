import datetime
import itertools
from collections import OrderedDict
from typing import Optional

from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Max, Min
from django.http import HttpRequest, HttpResponse, Http404, JsonResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect, resolve_url
from django.utils.decorators import method_decorator
from django.views.generic import FormView
from django.views.generic.edit import ModelFormMixin, UpdateView

from coredata.models import CourseOffering, Member
from courselib.auth import requires_course_by_slug, requires_course_staff_by_slug, ForbiddenResponse, HttpError
from courselib.search import find_member
from grades.models import Activity
from quizzes.forms import QuizForm, StudentForm, TimeSpecialCaseForm
from quizzes.models import Quiz, QUESTION_TYPE_CHOICES, QUESTION_CLASSES, Question, QuestionAnswer, TimeSpecialCase


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

    start, end = quiz.get_start_end(member)
    now = datetime.datetime.now()
    if start > now:
        context = {
            'offering': offering,
            'activity': activity,
            'quiz': quiz,
            'start': start,
            'end': end,
            'time': 'before'
        }
        return render(request, 'quizzes/unavailable.html', context=context)
    elif end < now: # TODO: should there be a 30 second grace period or something?
        context = {
            'offering': offering,
            'activity': activity,
            'quiz': quiz,
            'start': start,
            'end': end,
            'time': 'after'
        }
        return render(request, 'quizzes/unavailable.html', context=context)

    questions = Question.objects.filter(quiz=quiz)
    question_lookup = {q.ident(): q for q in questions}
    question_number = {q.id: i + 1 for i, q in enumerate(questions)}


    answers = list(QuestionAnswer.objects.filter(question__in=questions, student=member))
    answer_lookup = {a.question.ident(): a for a in answers}

    if request.method == 'POST':
        form = StudentForm(data=request.POST, files=request.FILES)
        # Don't need questionanswer when constructing fields here, because the values are already injected from the
        # form data in the previous line.
        fields = OrderedDict((q.ident(), q.entry_field(questionanswer=None)) for i, q in enumerate(questions))
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
                    ans.modified_at = datetime.datetime.now()
                    ans.answer = answer
                    ans.save()
                    messages.add_message(request, messages.INFO, 'Question #%i answer saved.' % (n,))

            messages.add_message(request, messages.SUCCESS, 'Quiz answers saved. You can continue to modify them, as long as you submit before the end of the quiz time.')
            return redirect('offering:quiz:index', course_slug=offering.slug, activity_slug=activity.slug)

    else:
        form = StudentForm()
        fields = OrderedDict(
            (q.ident(), q.entry_field(questionanswer=answer_lookup.get(q.ident(), None)))
            for i, q in enumerate(questions)
        )
        form.fields = fields

    question_data = list(zip(questions, form.visible_fields()))

    context = {
        'offering': offering,
        'activity': activity,
        'quiz': quiz,
        'questions': questions,
        'question_data': question_data,
        'form': form,
        'preview': False,
        'start': start,
        'end': end,
    }
    return render(request, 'quizzes/index_student.html', context=context)


@requires_course_staff_by_slug
def preview_student(request: HttpRequest, course_slug: str, activity_slug: str) -> HttpResponse:
    """
    Instructor's preview of what students will see
    """
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering)
    quiz = get_object_or_404(Quiz, activity=activity)
    questions = Question.objects.filter(quiz=quiz)

    fields = OrderedDict((q.ident(), q.entry_field()) for i, q in enumerate(questions))
    form = StudentForm()
    form.fields = fields

    question_data = list(zip(questions, form.visible_fields()))
    start, end = quiz.get_start_end(member=None)
    context = {
        'offering': offering,
        'activity': activity,
        'quiz': quiz,
        'questions': questions,
        'question_data': question_data,
        'preview': True,
        'start': start,
        'end': end,
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
        quiz = self.object
        context['quiz'] = quiz
        if quiz:
            context['offering'] = quiz.activity.offering
            context['activity'] = quiz.activity
        else:
            context['activity'] = get_object_or_404(Activity, slug=self.kwargs['activity_slug'],
                                                    offering__slug=self.kwargs['course_slug'])
            context['offering'] = context['activity'].offering

        return context


@requires_course_staff_by_slug
def question_add(request: HttpRequest, course_slug: str, activity_slug: str) -> HttpResponse:
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering)
    quiz = get_object_or_404(Quiz, activity=activity)

    if quiz.completed():
        return ForbiddenResponse(request, 'quiz is completed. You cannot edit questions after the end of the quiz time')

    if request.method == 'GET' and 'type' not in request.GET:
        # ask for type of question
        context = {
            'offering': offering,
            'activity': activity,
            'quiz': quiz,
            'question_type_choices': QUESTION_TYPE_CHOICES,
        }
        return render(request, 'quizzes/question_type.html', context=context)

    return _question_edit(request, offering, activity, quiz, question=None)


@requires_course_staff_by_slug
def question_edit(request: HttpRequest, course_slug: str, activity_slug: str, question_id: str) -> HttpResponse:
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering)
    quiz = get_object_or_404(Quiz, activity=activity)
    question = get_object_or_404(Question, quiz=quiz, id=question_id)

    if quiz.completed():
        return ForbiddenResponse(request, 'quiz is completed. You cannot edit questions after the end of the quiz time')

    return _question_edit(request, offering, activity, quiz, question)


def _question_edit(request: HttpRequest, offering: CourseOffering, activity: Activity, quiz: Quiz, question: Optional[Question] = None) -> HttpResponse:
    assert request.member.role in ['INST', 'TA']

    context = {
        'offering': offering,
        'activity': activity,
        'quiz': quiz,
        'editing': True,
    }

    if question is None:
        context['editing'] = False
        # creating a new Question: must have ?type= in URL to get here, then create it...
        if 'type' not in request.GET:
            raise Http404()
        qtype = request.GET['type']
        if qtype not in QUESTION_CLASSES:
            raise Http404()

        question = Question(quiz=quiz, type=qtype)

    helper = question.helper()

    if request.method == 'POST':
        form = helper.make_config_form(instance=question, data=request.POST, files=request.FILES)
        if form.is_valid():
            question.config = form.to_jsonable()
            question.set_order()
            question.save()
            messages.add_message(request, messages.SUCCESS, 'Question added.')
            return redirect('offering:quiz:index', course_slug=offering.slug, activity_slug=activity.slug)

    elif request.method == 'GET':
        form = helper.make_config_form(instance=question)

    context['question_helper'] = helper
    context['form'] = form
    context['question'] = question
    return render(request, 'quizzes/edit_question.html', context=context)


@requires_course_staff_by_slug
def question_reorder(request: HttpRequest, course_slug: str, activity_slug: str, question_id: str) -> HttpResponse:
    quiz = get_object_or_404(Quiz, activity__slug=activity_slug, activity__offering__slug=course_slug)
    question1 = get_object_or_404(Question, quiz=quiz, id=question_id)

    direction = request.GET.get('direction', '')
    if direction not in ['up', 'down']:
        raise Http404()

    if quiz.completed():
        return ForbiddenResponse(request, 'Quiz is completed. You cannot modify questions after the end of the quiz time')

    try:
        if direction == 'up':
            # find question before this one
            prev_order = Question.objects.filter(quiz=quiz, order__lt=question1.order).aggregate(Max('order'))['order__max']
            question2 = Question.objects.get(quiz=quiz, order=prev_order)
        else:
            # find question after this one
            next_order = Question.objects.filter(quiz=quiz, order__gt=question1.order).aggregate(Min('order'))['order__min']
            question2 = Question.objects.get(quiz=quiz, order=next_order)

    except Question.DoesNotExist:
        # moving up past the start, or down past the end: ignore
        pass

    else:
        o1 = question1.order
        o2 = question2.order
        with transaction.atomic():
            question2.order = o1
            question2.save()
            question1.order = o2
            question1.save()

    return HttpResponseRedirect(resolve_url('offering:quiz:index', course_slug=course_slug, activity_slug=activity_slug)
                                + '#q-' + str(question1.id))


@requires_course_staff_by_slug
def question_delete(request: HttpRequest, course_slug: str, activity_slug: str, question_id: str) -> HttpResponse:
    if request.method in ['POST', 'DELETE']:
        quiz = get_object_or_404(Quiz, activity__slug=activity_slug, activity__offering__slug=course_slug)
        question = get_object_or_404(Question, quiz=quiz, id=question_id)
        question.status = 'D'
        question.save()
        messages.add_message(request, messages.SUCCESS, 'Question deleted.')
        return redirect('offering:quiz:index', course_slug=course_slug, activity_slug=activity_slug)
    else:
        return HttpError(request, status=405, title="Method Not Allowed", error='POST or DELETE requests only.')


@requires_course_staff_by_slug
def submissions(request: HttpRequest, course_slug: str, activity_slug: str) -> HttpResponse:
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering)
    quiz = get_object_or_404(Quiz, activity=activity)
    questions = Question.objects.filter(quiz=quiz)

    answers = QuestionAnswer.objects.filter(question__in=questions) \
        .select_related('student__person') \
        .order_by('student__person')

    by_student = itertools.groupby(answers, key=lambda a: a.student)
    subs = [(member, max(a.modified_at for a in ans)) for member, ans in by_student]

    context = {
        'offering': offering,
        'activity': activity,
        'quiz': quiz,
        'submissions': subs,
    }
    return render(request, 'quizzes/submissions.html', context=context)


@requires_course_staff_by_slug
def download_submissions(request: HttpRequest, course_slug: str, activity_slug: str) -> HttpResponse:
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering)
    quiz = get_object_or_404(Quiz, activity=activity)
    questions = Question.objects.filter(quiz=quiz)

    answers = QuestionAnswer.objects.filter(question__in=questions) \
        .select_related('student__person') \
        .order_by('student__person')

    by_student = itertools.groupby(answers, key=lambda a: a.student)
    data = []
    for m, answers in by_student:
        answers = list(answers)
        answers_lookup = {a.question_id: a for a in answers}
        lastmod = max(a.modified_at for a in answers)
        d = {
            'userid': m.person.userid_or_emplid(),
            'last_submission': lastmod,
        }
        d.update({
            'q-%i'%(i+1): q.helper().to_text(answers_lookup[q.id]) if q.id in answers_lookup else None
            for i, q in enumerate(questions)
        })
        data.append(d)

    return JsonResponse({'submissions': data})


@requires_course_staff_by_slug
def view_submission(request: HttpRequest, course_slug: str, activity_slug: str, userid: str) -> HttpResponse:
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering)
    quiz = get_object_or_404(Quiz, activity=activity)
    questions = Question.objects.filter(quiz=quiz)
    member = get_object_or_404(Member, ~Q(role='DROP'), find_member(userid), offering__slug=course_slug)
    answers = QuestionAnswer.objects.filter(student=member, question__in=questions).select_related('question')

    answer_lookup = {a.question_id: a for a in answers}
    question_answers = [(q, answer_lookup.get(q.id, None)) for q in questions]

    context = {
        'offering': offering,
        'activity': activity,
        'quiz': quiz,
        'member': member,
        'question_answers': question_answers,
    }
    return render(request, 'quizzes/view_submission.html', context=context)


@requires_course_staff_by_slug
def special_cases(request: HttpRequest, course_slug: str, activity_slug: str) -> HttpResponse:
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering)
    quiz = get_object_or_404(Quiz, activity=activity)
    special_cases = TimeSpecialCase.objects.filter(quiz=quiz).select_related('student', 'student__person')

    context = {
        'offering': offering,
        'activity': activity,
        'quiz': quiz,
        'special_cases': special_cases,
    }
    return render(request, 'quizzes/special_cases.html', context=context)


@requires_course_staff_by_slug
def special_case_add(request: HttpRequest, course_slug: str, activity_slug: str) -> HttpResponse:
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering)
    quiz = get_object_or_404(Quiz, activity=activity)
    students = Member.objects.filter(offering=offering, role='STUD').select_related('person')

    if request.method == 'POST':
        form = TimeSpecialCaseForm(quiz=quiz, students=students, data=request.POST)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Special case saved.')
            return redirect('offering:quiz:special_cases', course_slug=offering.slug, activity_slug=activity.slug)
    else:
        start, end = quiz.get_start_end(member=None)
        form = TimeSpecialCaseForm(quiz=quiz, students=students, initial={'start': start, 'end': end})

    context = {
        'offering': offering,
        'activity': activity,
        'quiz': quiz,
        'form': form,
    }
    return render(request, 'quizzes/special_case_add.html', context=context)

@requires_course_staff_by_slug
def special_case_delete(request: HttpRequest, course_slug: str, activity_slug: str, sc_id: str) -> HttpResponse:
    if request.method in ['POST', 'DELETE']:
        sc = get_object_or_404(TimeSpecialCase, quiz__activity__offering__slug=course_slug, quiz__activity__slug=activity_slug, id=sc_id)
        sc.delete()
        messages.add_message(request, messages.SUCCESS, 'Special case deleted.')
        return redirect('offering:quiz:special_cases', course_slug=course_slug, activity_slug=activity_slug)
    else:
        return HttpError(request, status=405, title="Method Not Allowed", error='POST or DELETE requests only.')
