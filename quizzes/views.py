import datetime
import decimal
import itertools
import random
from collections import OrderedDict
from typing import Optional, Tuple, List

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
from grades.models import Activity, NumericGrade
from log.models import LogEntry
from marking.models import ActivityComponent, ActivityComponentMark, StudentActivityMark, get_activity_mark_for_student
from quizzes.forms import QuizForm, StudentForm, TimeSpecialCaseForm, MarkingForm, ComponentForm, MarkingSetupForm
from quizzes.models import Quiz, QUESTION_TYPE_CHOICES, QUESTION_HELPER_CLASSES, Question, QuestionAnswer, \
    TimeSpecialCase, \
    QuizSubmission, QuestionVersion, MarkingNotConfiguredError


@requires_course_by_slug
def index(request: HttpRequest, course_slug: str, activity_slug: str) -> HttpResponse:
    role = request.member.role
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering, group=False)

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
    honour_code_key = 'previous_honour_code_' + str(quiz.id)
    previous_honour_code = request.session.get(honour_code_key, False)  # did student agree to honour code recently?

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
                if name == 'photo-capture':
                    continue

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
            if request.POST.get('honour-code', None):
                request.session[honour_code_key] = True

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
        'seconds_left': (end - datetime.datetime.now()).total_seconds(),
        'previous_honour_code': bool(previous_honour_code),
    }
    return render(request, 'quizzes/index_student.html', context=context)


@requires_course_staff_by_slug
def preview_student(request: HttpRequest, course_slug: str, activity_slug: str) -> HttpResponse:
    """
    Instructor's preview of what students will see
    """
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering, group=False)
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
        'seconds_left': (end - datetime.datetime.now()).total_seconds(),
    }
    return render(request, 'quizzes/index_student.html', context=context)


@method_decorator(requires_course_staff_by_slug, name='dispatch')
class EditView(FormView, UpdateView, ModelFormMixin):
    model = Quiz
    form_class = QuizForm
    template_name = 'quizzes/edit.html'

    def get_object(self, queryset=None):
        activity = get_object_or_404(Activity, slug=self.kwargs['activity_slug'],
                                     offering__slug=self.kwargs['course_slug'], group=False)
        quiz = Quiz.objects.filter(activity=activity).first() # None if no Quiz created
        return quiz

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        activity = get_object_or_404(Activity, slug=self.kwargs['activity_slug'],
                                     offering__slug=self.kwargs['course_slug'], group=False)
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
        LogEntry(userid=self.request.user.username, description='edited quiz id=%i' % (self.object.id,),
                 related_object=self.object).save()

        messages.add_message(self.request, messages.SUCCESS, 'Quiz details updated.')

        if self.object.activity.due_date != self.object.end:
            self.object.activity.due_date = self.object.end
            self.object.activity.save()
            messages.add_message(self.request, messages.INFO, 'Updated %s due date to match quiz end.' % (self.object.activity.name,))

        return res


@requires_course_staff_by_slug
def question_add(request: HttpRequest, course_slug: str, activity_slug: str) -> HttpResponse:
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering, group=False)
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
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering, group=False)
    quiz = get_object_or_404(Quiz, activity=activity)
    question = get_object_or_404(Question, quiz=quiz, id=question_id)
    version = get_object_or_404(QuestionVersion.objects.select_related('question'), question=question, id=version_id)

    if quiz.completed():
        return ForbiddenResponse(request, 'quiz is completed. You cannot edit questions after the end of the quiz time')

    return _question_edit(request, offering, activity, quiz, question, version)


@requires_course_staff_by_slug
def question_add_version(request: HttpRequest, course_slug: str, activity_slug: str, question_id: str) -> HttpResponse:
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering, group=False)
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
        if qtype not in QUESTION_HELPER_CLASSES:
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
            if question.is_dirty():
                question.save()
                if activity.quiz_marking():
                    # updated question, and are configured for quiz-based marking: update that
                    quiz.configure_marking(delete_others=False)
                    messages.add_message(request, messages.INFO, 'Updated marking rubric to match quiz questions.')
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
            if quiz.activity.quiz_marking():
                # configured for quiz-based marking: update that so the order matches
                quiz.configure_marking(delete_others=False)
                messages.add_message(request, messages.INFO, 'Reordered marking rubric to match quiz questions.')

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
        if quiz.activity.quiz_marking():
            # configured for quiz-based marking: update that so the order matches
            quiz.configure_marking(delete_others=False)
            messages.add_message(request, messages.INFO, 'Updated marking rubric to match quiz questions.')
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
        other_versions = QuestionVersion.objects.filter(question=question).exclude(id=version_id)
        if not other_versions.exists():
            messages.add_message(request, messages.ERROR, 'Cannot delete the only version of a question.')
            return redirect('offering:quiz:question_edit', course_slug=course_slug, activity_slug=activity_slug, question_id=question_id, version_id=version_id)
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
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering, group=False)
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
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering, group=False)
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
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering, group=False)
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
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering, group=False)
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
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering, group=False)
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
def submission_photo(request: HttpRequest, course_slug: str, activity_slug: str, userid: str, submission_id: str) -> StreamingHttpResponse:
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering, group=False)
    quiz = get_object_or_404(Quiz, activity=activity)
    member = get_object_or_404(Member, ~Q(role='DROP'), find_member(userid), offering__slug=course_slug)
    submission = get_object_or_404(QuizSubmission, id=submission_id, quiz=quiz, student=member)
    if not submission.capture:
        raise Http404

    resp = StreamingHttpResponse(streaming_content=submission.capture, content_type='image/png', status=200)
    resp['Content-Disposition'] = 'inline; filename="%s.png"' % (userid,)
    return resp


@requires_course_staff_by_slug
def special_cases(request: HttpRequest, course_slug: str, activity_slug: str) -> HttpResponse:
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering, group=False)
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
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering, group=False)
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


def catch_marking_configuration_error(f):
    """
    Decorator to catch MarkingNotConfiguredError and redirect, offering to set things up.
    """
    def decorate(request: HttpRequest, course_slug: str, activity_slug: str, *args, **kwargs):
        with transaction.atomic():
            try:
                return f(request=request, course_slug=course_slug, activity_slug=activity_slug, *args, **kwargs)
            except MarkingNotConfiguredError:
                messages.add_message(request, messages.WARNING, 'Marking is not configured for this quiz.')
                return redirect('offering:quiz:marking_setup', course_slug=course_slug, activity_slug=activity_slug)

    return decorate


def marking_setup(request: HttpRequest, course_slug: str, activity_slug: str) -> HttpResponse:
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering, group=False)
    quiz = get_object_or_404(Quiz, activity=activity)

    components = ActivityComponent.objects.filter(numeric_activity_id=activity.id, deleted=False)
    other_components = [c for c in components if c.config.get('quiz-question-id', None) is None]

    if request.method == 'POST':
        form = MarkingSetupForm(data=request.POST)
        if form.is_valid():
            quiz.configure_marking(delete_others=form.cleaned_data['delete_others'])
            messages.add_message(request, messages.SUCCESS, 'Marking configured for this activity and quiz.')
            LogEntry(userid=request.user.username, description='configured quiz marking for %s' % (activity.name,),
                     related_object=quiz).save()
            return redirect('offering:quiz:marking', course_slug=offering.slug, activity_slug=activity.slug)
    else:
        form = MarkingSetupForm()

    context = {
        'offering': offering,
        'activity': activity,
        'quiz': quiz,
        'form': form,
        'other_components': other_components,
    }
    return render(request, 'quizzes/marking_setup.html', context=context)


@requires_course_staff_by_slug
@catch_marking_configuration_error
def marking(request: HttpRequest, course_slug: str, activity_slug: str) -> HttpResponse:
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering, group=False)
    quiz = get_object_or_404(Quiz, activity=activity)
    questions = Question.objects.filter(quiz=quiz)
    versions = QuestionVersion.objects.filter(question__quiz=quiz)
    components = ActivityComponent.objects.filter(numeric_activity_id=quiz.activity_id, deleted=False)
    comp_marks = ActivityComponentMark.objects.filter(activity_component__in=components) \
        .select_related('activity_mark', 'activity_component')
    comp_marks = list(comp_marks)
    if not activity.quiz_marking():
        raise MarkingNotConfiguredError

    # collect existing marks for tally
    component_lookup = quiz.activitycomponents_by_question()
    version_lookup = {q_id: list(vs) for q_id, vs in itertools.groupby(versions, key=lambda v: v.question_id)}
    question_marks: List[Tuple[Question, List[ActivityComponentMark]]] = []
    for q in questions:
        if q not in component_lookup:
            raise MarkingNotConfiguredError('Marking not configured')
        comp = component_lookup[q]
        marks = [m for m in comp_marks if m.activity_component == comp and m.value is not None]
        vs = version_lookup[q.id]
        question_marks.append((q, marks, vs))

    # data for all marks table
    answers = QuestionAnswer.objects.filter(question__quiz=quiz).select_related('student__person')
    student_marks = StudentActivityMark.objects.filter(activity=activity).select_related('numeric_grade')
    student_mark_lookup = {am.numeric_grade.member_id: am.id for am in student_marks} # map Member.id to ActivityMark.id
    students = {a.student for a in answers}
    comp_mark_lookup = {(cm.activity_mark_id, cm.activity_component_id): cm for cm in comp_marks}
    student_mark_data = [] # pairs of (Member, list of marks for each question)
    for s in students:
        student_marks = []
        for q in questions:
            # see if we have a mark for student s on question q
            comp = component_lookup[q]
            am_id = student_mark_lookup.get(s.id, None)
            if not am_id:
                student_marks.append(None)
            else:
                student_marks.append(comp_mark_lookup.get((am_id, comp.id), None))

        student_mark_data.append((s, student_marks))

    context = {
        'offering': offering,
        'activity': activity,
        'quiz': quiz,
        'question_marks': question_marks,
        'student_mark_data': student_mark_data,
    }
    return render(request, 'quizzes/marking.html', context=context)


@requires_course_staff_by_slug
@catch_marking_configuration_error
def mark_next(request: HttpRequest, course_slug: str, activity_slug: str,
              question_id: Optional[str] = None, version_id: Optional[str] = None) -> HttpResponse:
    """
    Mark random quiz with given question unmarked.
    """
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering, group=False)
    quiz = get_object_or_404(Quiz, activity=activity)
    component_lookup = quiz.activitycomponents_by_question()
    if not activity.quiz_marking():
        raise MarkingNotConfiguredError

    if question_id:
        question = get_object_or_404(Question, quiz=quiz, id=question_id)
        try:
            component = component_lookup[question]
        except KeyError:
            raise MarkingNotConfiguredError('Marking not configured')
    else:
        question = None

    if question and version_id:
        version = get_object_or_404(QuestionVersion, question=question, id=version_id)
    else:
        version = None

    # Find QuestionAnswers that don't have a corresponding mark.
    # This is a bit of a pain because of the marking model structure, but it's too late to change that now.
    if version:
        answers = QuestionAnswer.objects.filter(question=question, question_version=version).select_related('student')
        comp_marks = ActivityComponentMark.objects.filter(activity_component=component, value__isnull=False)
    elif question:
        answers = QuestionAnswer.objects.filter(question=question).select_related('student')
        comp_marks = ActivityComponentMark.objects.filter(activity_component=component, value__isnull=False)
    else:
        answers = QuestionAnswer.objects.filter(question__quiz=quiz).select_related('student')
        comp_marks = ActivityComponentMark.objects.filter(activity_component__numeric_activity_id=activity.id, value__isnull=False)
    activity_mark_ids = set(cm.activity_mark_id for cm in comp_marks)
    activity_marks = StudentActivityMark.objects.filter(id__in=activity_mark_ids).select_related('numeric_grade__member')

    answering_students = set(a.student for a in answers)
    marked_students = set(am.numeric_grade.member for am in activity_marks)
    unmarked_students = answering_students - marked_students

    # pick one and redirect to mark them
    unmarked_students = list(unmarked_students)
    if unmarked_students:
        student = random.choice(unmarked_students)
        url = resolve_url('offering:quiz:mark_student',
                          course_slug=course_slug, activity_slug=activity_slug, member_id=student.id)
        if question:
            return HttpResponseRedirect(url + '#' + str(question.ident()))
        else:
            return HttpResponseRedirect(url)
    else:
        if version:
            messages.add_message(request, messages.INFO, 'That version has been completely marked.')
        elif question:
            messages.add_message(request, messages.INFO, 'That question has been completely marked.')
        else:
            messages.add_message(request, messages.INFO, 'Marking complete.')
        return HttpResponseRedirect(
            resolve_url('offering:quiz:marking',
                        course_slug=course_slug, activity_slug=activity_slug))


@requires_course_staff_by_slug
@catch_marking_configuration_error
def mark_student(request: HttpRequest, course_slug: str, activity_slug: str, member_id: str) -> HttpResponse:
    # using Member.id in the URL instead of Member.person.userid for vague anonymity in the URL.
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=offering, group=False)
    quiz = get_object_or_404(Quiz, activity=activity)
    member = get_object_or_404(Member, id=member_id, offering=offering)
    answers = QuestionAnswer.objects.filter(question__quiz=quiz, student=member)
    questions = Question.objects.filter(quiz=quiz)
    versions = QuestionVersion.select(quiz=quiz, questions=questions, student=member, answers=answers)
    all_versions = QuestionVersion.objects.filter(question__quiz=quiz).select_related('question')
    if not activity.quiz_marking():
        raise MarkingNotConfiguredError

    answer_lookup = {a.question_id: a for a in answers}
    component_lookup = quiz.activitycomponents_by_question()

    # find existing marks for this student
    mark = get_activity_mark_for_student(activity, member)
    component_marks = ActivityComponentMark.objects.filter(activity_mark=mark)
    component_mark_lookup = {acm.activity_component_id: acm for acm in component_marks}

    if request.method == 'POST':
        # build forms from POST data
        form = MarkingForm(data=request.POST, activity=activity, instance=mark)
        component_form_lookup = {}
        by_component_lookup = {}
        for q in questions:
            try:
                ac = component_lookup[q]
            except KeyError:
                raise MarkingNotConfiguredError('Marking not configured')
            acm = component_mark_lookup.get(ac.id, None)
            f = ComponentForm(data=request.POST, component=ac, prefix=q.ident(), instance=acm)
            component_form_lookup[q.id] = f
            by_component_lookup[ac] = f

        if form.is_valid() and all(f.is_valid() for f in component_form_lookup.values()):
            # NOTE: this logic is largely duplicated from marking.views._marking_view. Ugly, but the least-worst way.
            # TODO: there is a race here if two TAs are marking different questions simultaneously
            am = form.save(commit=False)
            am.pk = None
            am.id = None
            am.created_by = request.user.username
            am.activity_id = activity.id

            # need a corresponding NumericGrade object: find or create one
            try:
                ngrade = NumericGrade.objects.get(activity=activity, member=member)
            except NumericGrade.DoesNotExist:
                ngrade = NumericGrade(activity_id=activity.id, member=member)
                ngrade.save(newsitem=False, entered_by=None, is_temporary=True)
            am.numeric_grade = ngrade

            # calculate grade and save
            total = decimal.Decimal(0)
            components_not_all_there = False
            for component in component_lookup.values():
                f = by_component_lookup[component]
                value = f.cleaned_data['value']
                if value is None:
                    components_not_all_there = True
                else:
                    total += value
                    if value > component.max_mark:
                        messages.add_message(request, messages.WARNING,
                                             "Bonus marks given for %s" % (component.title))
                    if value < 0:
                        messages.add_message(request, messages.WARNING,
                                             "Negative mark given for %s" % (component.title))
            if not components_not_all_there:
                mark = (1 - form.cleaned_data['late_penalty'] / decimal.Decimal(100)) * \
                       (total - form.cleaned_data['mark_adjustment'])
            else:
                mark = None

            am.setMark(mark, entered_by=request.user.username)
            am.save()
            form.save_m2m()
            for component in component_lookup.values():
                f = by_component_lookup[component]
                c = f.save(commit=False)
                c.activity_component = component
                c.activity_mark = am
                c.save()
                f.save_m2m()

            messages.add_message(request, messages.SUCCESS, 'Marks saved.')
            LogEntry(userid=request.user.username, description='marked quiz on %s for %s' % (activity.name, member.person.userid_or_emplid()),
                     related_object=am).save()

            # Where to now? Did they click a "next Q#n" or "next Q#n verm" button?
            next_q_button = [k for k in request.POST.keys() if k.startswith('mark-next-q-')]
            next_v_button = [k for k in request.POST.keys() if k.startswith('mark-nextver-q-')]
            if next_v_button:
                q_id, v_id = next_v_button[0].replace('mark-nextver-q-', '').split('-')
                return redirect('offering:quiz:mark_next_version', course_slug=offering.slug, activity_slug=activity.slug, question_id=q_id, version_id=v_id)
            elif next_q_button:
                q_id = next_q_button[0].replace('mark-next-q-', '')
                return redirect('offering:quiz:mark_next_question', course_slug=offering.slug, activity_slug=activity.slug, question_id=q_id)
            else:
                # Nope. Go to any "next" quiz.
                return redirect('offering:quiz:mark_next', course_slug=offering.slug, activity_slug=activity.slug)

    else:
        # build forms from existing marking data
        form = MarkingForm(activity=activity, instance=mark)
        component_form_lookup = {}
        for q in questions:
            try:
                ac = component_lookup[q]
            except KeyError:
                raise MarkingNotConfiguredError('Marking not configured')
            acm = component_mark_lookup.get(ac.id, None)
            f = ComponentForm(component=ac, prefix=q.ident(), instance=acm)
            component_form_lookup[q.id] = f

    # enumerate versions of each question, so we know if the "next version n" button is relevant
    num_versions_lookup = {q_id: len(list(versions)) for q_id, versions in itertools.groupby(all_versions, key=lambda v: v.question_id)}

    # data struct with all the per-question stuff needed
    version_form_answers = [
        (v,
         component_form_lookup[v.question_id],
         answer_lookup.get(v.question_id, None),
         num_versions_lookup[v.question_id])
        for v in versions]

    context = {
        'offering': offering,
        'activity': activity,
        'quiz': quiz,
        'member': member,
        'version_form_answers': version_form_answers,
        'form': form,
    }
    return render(request, 'quizzes/mark_student.html', context=context)
