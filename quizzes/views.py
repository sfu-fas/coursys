import datetime
import itertools
from collections import OrderedDict
from typing import Optional

from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Max, Min
from django.http import HttpRequest, HttpResponse, Http404, JsonResponse, HttpResponseRedirect, StreamingHttpResponse
from django.shortcuts import render, get_object_or_404, redirect, resolve_url
from django.utils.decorators import method_decorator
from django.views.generic import FormView
from django.views.generic.edit import ModelFormMixin, UpdateView

from coredata.models import CourseOffering, Member
from courselib.auth import requires_course_by_slug, requires_course_staff_by_slug, ForbiddenResponse, HttpError
from courselib.search import find_member
from grades.models import Activity
from log.models import LogEntry
from quizzes.forms import QuizForm, StudentForm, TimeSpecialCaseForm
from quizzes.models import Quiz, QUESTION_TYPE_CHOICES, QUESTION_CLASSES, Question, QuestionAnswer, TimeSpecialCase, \
    QuizSubmission, QuestionVersion


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


@transaction.atomic
def _index_student(request: HttpRequest, offering: CourseOffering, activity: Activity, quiz: Quiz) -> HttpResponse:
    member = request.member
    assert member.role == 'STUD'

    # Overtime logic: cannot display the quiz (i.e. page with form), period. Submitting form will be accepted up to
    # 5 minutes late, with timestamp to allow instructor to interpret as they see fit.
    start, end = quiz.get_start_end(member)
    now = datetime.datetime.now()
    grace = datetime.timedelta(seconds=quiz.grace)
    if start > now:
        # early
        context = {
            'offering': offering,
            'activity': activity,
            'quiz': quiz,
            'start': start,
            'end': end,
            'time': 'before'
        }
        return render(request, 'quizzes/unavailable.html', context=context, status=403)
    elif (end < now and request.method == 'GET') or (end + grace < now):
        # late
        context = {
            'offering': offering,
            'activity': activity,
            'quiz': quiz,
            'start': start,
            'end': end,
            'time': 'after'
        }
        return render(request, 'quizzes/unavailable.html', context=context, status=403)

    am_late = end < now  # checked below to decide message to give to student when submitting during grace period

    questions = Question.objects.filter(quiz=quiz)
    question_number = {q.id: i + 1 for i, q in enumerate(questions)}

    answers = list(QuestionAnswer.objects.filter(question__in=questions, student=member))
    answer_lookup = {a.question.ident(): a for a in answers}

    versions = QuestionVersion.select(quiz=quiz, questions=questions, student=member, answers=answers)
    version_lookup = {v.question.ident(): v for v in versions}

    if request.method == 'POST':
        form = StudentForm(data=request.POST, files=request.FILES)
        fields = OrderedDict(
            (v.question.ident(), v.entry_field(student=member, questionanswer=answer_lookup.get(v.question.ident(), None)))
            for v in versions
        )
        form.fields = fields

        if form.is_valid():
            # Iterate through each answer we received, and create/update corresponding QuestionAnswer objects.
            answers = []
            for name, data in form.cleaned_data.items():
                try:
                    vers = version_lookup[name]
                except KeyError:
                    continue # Submitted a question that doesn't exist? Ignore

                n = question_number[vers.question.id]
                helper = vers.helper()
                answer = helper.to_jsonable(data)

                if name in answer_lookup:
                    # Have an existing QuestionAnswer: update only if answer has changed.
                    ans = answer_lookup[name]
                    if helper.unchanged_answer(ans.answer, answer):
                        messages.add_message(request, messages.INFO, 'Question #%i answer unchanged from previous submission.' % (n,))
                    else:
                        ans.modified_at = datetime.datetime.now()
                        ans.answer = answer
                        ans.save()
                        answers.append(ans)
                        messages.add_message(request, messages.INFO, 'Question #%i answer saved.' % (n,))

                else:
                    # No existing QuestionAnswer: create one.
                    ans = QuestionAnswer(question=vers.question, question_version=vers, student=member)
                    ans.modified_at = datetime.datetime.now()
                    ans.answer = answer
                    ans.save()
                    answers.append(ans)
                    messages.add_message(request, messages.INFO, 'Question #%i answer saved.' % (n,))
                    LogEntry(userid=request.user.username, description='submitted quiz question %i' % (vers.question.id),
                             related_object=ans).save()

            QuizSubmission.create(request=request, quiz=quiz, student=member, answers=answers)

            if am_late:
                messages.add_message(request, messages.SUCCESS, 'Quiz answers saved, but the quiz is now over and you cannot edit further.')
                messages.add_message(request, messages.WARNING, 'Your submission was %i seconds after the end of the quiz: the instructor will determine how this will affect the marking.'
                                     % ((now - end).total_seconds(),))
                # redirect should be to the "unavailable" logic above.
                return redirect('offering:quiz:index', course_slug=offering.slug, activity_slug=activity.slug)
            else:
                messages.add_message(request, messages.SUCCESS,
                                     'Quiz answers saved. You can continue to modify them, as long as you submit before '
                                     'the end of the quiz time.')
                return redirect('offering:quiz:index', course_slug=offering.slug, activity_slug=activity.slug)

    else:
        form = StudentForm()
        fields = OrderedDict(
            (v.question.ident(), v.entry_field(student=member, questionanswer=answer_lookup.get(v.question.ident(), None)))
            for v in versions
        )
        form.fields = fields

    question_data = list(zip(questions, versions, form.visible_fields()))

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
    versions = QuestionVersion.select(quiz=quiz, questions=questions, student=None, answers=None)

    fields = OrderedDict((v.question.ident(), v.entry_field(student=None)) for i, v in enumerate(versions))
    form = StudentForm()
    form.fields = fields

    question_data = list(zip(questions, versions, form.visible_fields()))
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

    def form_valid(self, form):
        res = super().form_valid(form)
        LogEntry(userid=self.request.user.username, description='edited quiz id=%i' % (self.object.id),
                 related_object=self.object).save()
        return res


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

    return _question_edit(request, offering, activity, quiz, question=None, version=None)


@requires_course_staff_by_slug
def question_edit(request: HttpRequest, course_slug: str, activity_slug: str, question_id: str, version_id: str) -> HttpResponse:
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering)
    quiz = get_object_or_404(Quiz, activity=activity)
    question = get_object_or_404(Question, quiz=quiz, id=question_id)
    version = get_object_or_404(QuestionVersion.objects.select_related('question'), question=question, id=version_id)

    if quiz.completed():
        return ForbiddenResponse(request, 'quiz is completed. You cannot edit questions after the end of the quiz time')

    return _question_edit(request, offering, activity, quiz, question, version)


@requires_course_staff_by_slug
def question_add_version(request: HttpRequest, course_slug: str, activity_slug: str, question_id: str) -> HttpResponse:
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering)
    quiz = get_object_or_404(Quiz, activity=activity)
    question = get_object_or_404(Question, quiz=quiz, id=question_id)

    if quiz.completed():
        return ForbiddenResponse(request, 'quiz is completed. You cannot edit questions after the end of the quiz time')

    return _question_edit(request, offering, activity, quiz, question, version=None)


@transaction.atomic
def _question_edit(request: HttpRequest, offering: CourseOffering, activity: Activity, quiz: Quiz,
                   question: Optional[Question] = None, version: Optional[QuestionVersion] = None) -> HttpResponse:
    assert request.member.role in ['INST', 'TA']

    context = {
        'offering': offering,
        'activity': activity,
        'quiz': quiz,
    }

    if question is None:
        # creating a new Question
        assert version is None
        # creating a new Question: must have ?type= in URL to get here, then create it...
        if 'type' not in request.GET:
            raise Http404()
        qtype = request.GET['type']
        if qtype not in QUESTION_CLASSES:
            raise Http404()

        question = Question(quiz=quiz, type=qtype)
        version = QuestionVersion(question=question)
        action = 'new_q'
    elif version is None:
        # creating a new QuestionVersion
        version = QuestionVersion(question=question)
        action = 'new_v'
    else:
        # editing a QuestionVersion
        assert version.question_id == question.id
        action = 'edit'

    helper = version.helper(question=question)

    if request.method == 'POST':
        form = helper.make_config_form(data=request.POST, files=request.FILES)
        if form.is_valid():
            data = form.to_jsonable()
            # save the Question
            question.config['points'] = data['points']
            question.set_order()
            question.save()
            # save the QuestionVersion
            del data['points']
            version.question = question
            version.config = data
            version.save()

            if action == 'new_q':
                messages.add_message(request, messages.SUCCESS, 'Question added.')
            else:
                messages.add_message(request, messages.SUCCESS, 'Question updated.')
            LogEntry(userid=request.user.username, description='edited quiz question.id=%i, version_id=%i' % (question.id, version.id),
                     related_object=question).save()
            return redirect('offering:quiz:index', course_slug=offering.slug, activity_slug=activity.slug)

    elif request.method == 'GET':
        form = helper.make_config_form()

    context['question_helper'] = helper
    context['form'] = form
    context['question'] = question
    context['version'] = version
    context['action'] = action
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
        if quiz.completed():
            return ForbiddenResponse(request, 'Quiz is completed. You cannot modify questions after the end of the quiz time')
        question = get_object_or_404(Question, quiz=quiz, id=question_id)
        question.status = 'D'
        question.save()
        messages.add_message(request, messages.SUCCESS, 'Question deleted.')
        LogEntry(userid=request.user.username, description='deleted quiz question id=%i' % (question.id,),
                 related_object=question).save()
        return redirect('offering:quiz:index', course_slug=course_slug, activity_slug=activity_slug)
    else:
        return HttpError(request, status=405, title="Method Not Allowed", error='POST or DELETE requests only.')


@requires_course_staff_by_slug
def version_delete(request: HttpRequest, course_slug: str, activity_slug: str, question_id: str, version_id: str) -> HttpResponse:
    if request.method in ['POST', 'DELETE']:
        quiz = get_object_or_404(Quiz, activity__slug=activity_slug, activity__offering__slug=course_slug)
        if quiz.completed():
            return ForbiddenResponse(request, 'Quiz is completed. You cannot modify questions after the end of the quiz time')
        question = get_object_or_404(Question, quiz=quiz, id=question_id)
        version = get_object_or_404(QuestionVersion, question=question, id=version_id)
        version.status = 'D'
        version.save()
        messages.add_message(request, messages.SUCCESS, 'Question version deleted.')
        LogEntry(userid=request.user.username, description='deleted quiz question version id=%i' % (question.id,),
                 related_object=question).save()
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

    students = set(a.student for a in answers)
    starts_ends = quiz.get_starts_ends(students)
    by_student = itertools.groupby(answers, key=lambda a: a.student)
    subs_late = [(member, max(a.modified_at for a in ans) - starts_ends[member][1]) for member, ans in by_student]

    context = {
        'offering': offering,
        'activity': activity,
        'quiz': quiz,
        'subs_late': subs_late,
        'timedelta_zero': datetime.timedelta(seconds=0)
    }
    return render(request, 'quizzes/submissions.html', context=context)


@requires_course_staff_by_slug
def download_submissions(request: HttpRequest, course_slug: str, activity_slug: str) -> HttpResponse:
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering)
    quiz = get_object_or_404(Quiz, activity=activity)
    questions = Question.objects.filter(quiz=quiz)
    versions = QuestionVersion.objects.filter(question__in=questions)
    version_number_lookup = {  # version_number_lookup[question_id][version_id] == version_number
        q_id: {v.id: i+1 for i,v in enumerate(vs)}
        for q_id, vs in itertools.groupby(versions, key=lambda v: v.question_id)
    }

    answers = QuestionAnswer.objects.filter(question__in=questions) \
        .select_related('student__person', 'question_version', 'question') \
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
            'q-%i'%(i+1):
                (
                    {
                        'version': version_number_lookup[q.id].get(answers_lookup[q.id].question_version_id, 0),
                        'answer': answers_lookup[q.id].question_version.helper(question=q).to_text(answers_lookup[q.id])
                    }
                    if q.id in answers_lookup else None
                )
            for i, q in enumerate(questions)
        })
        # The .get(...version_id, 0) returns 0 if a student answers a version, then the instructor deletes it. Hopefully never
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
    versions = QuestionVersion.select(quiz=quiz, questions=questions, student=member, answers=answers)

    answer_lookup = {a.question_id: a for a in answers}
    version_answers = [(v, answer_lookup.get(v.question.id, None)) for v in versions]

    context = {
        'offering': offering,
        'activity': activity,
        'quiz': quiz,
        'member': member,
        'version_answers': version_answers,
    }
    return render(request, 'quizzes/view_submission.html', context=context)


# This view is authorized by knowing the secret not by session, to allow automated downloads of submissions from JSON.
def submitted_file(request: HttpRequest, course_slug: str, activity_slug: str, userid: str, answer_id: str, secret: str) -> StreamingHttpResponse:
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering)
    member = get_object_or_404(Member, ~Q(role='DROP'), find_member(userid), offering__slug=course_slug)
    answer = get_object_or_404(QuestionAnswer, question__quiz__activity=activity, student=member, id=answer_id)

    real_secret = answer.answer['data'].get('secret', '?')
    if secret != real_secret or real_secret == '?':
        raise Http404()

    content_type = answer.answer['data'].get('content-type', 'application/octet-stream')
    charset = answer.answer['data'].get('charset', None)
    filename = answer.answer['data'].get('filename', None)
    data = answer.file.open('rb')

    resp = StreamingHttpResponse(streaming_content=data, content_type=content_type, charset=charset, status=200)
    if filename:
        resp['Content-Disposition'] = 'inline; filename="%s"' % (filename,)
    return resp


@requires_course_staff_by_slug
def submission_history(request: HttpRequest, course_slug: str, activity_slug: str, userid: str) -> HttpResponse:
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering)
    quiz = get_object_or_404(Quiz, activity=activity)
    questions = Question.objects.filter(quiz=quiz)
    versions = QuestionVersion.objects.filter(question__in=questions)
    member = get_object_or_404(Member, ~Q(role='DROP'), find_member(userid), offering__slug=course_slug)
    quiz_submissions = QuizSubmission.objects.filter(quiz=quiz, student=member)
    [qs.annotate_questions(questions, versions) for qs in quiz_submissions]

    context = {
        'offering': offering,
        'activity': activity,
        'quiz': quiz,
        'member': member,
        'quiz_submissions': quiz_submissions,
    }
    return render(request, 'quizzes/submission_history.html', context=context)


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
            sc = form.save()
            messages.add_message(request, messages.SUCCESS, 'Special case saved.')
            LogEntry(userid=request.user.username, description='added timing special case for %s' % (sc.student,),
                     related_object=sc).save()

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
        LogEntry(userid=request.user.username, description='deleted timing special case for %s' % (sc.student,),
                 related_object=sc.quiz).save()
        return redirect('offering:quiz:special_cases', course_slug=course_slug, activity_slug=activity_slug)
    else:
        return HttpError(request, status=405, title="Method Not Allowed", error='POST or DELETE requests only.')
