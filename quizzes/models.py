# TODO: delete Quiz?
# TODO: let instructor select "one question at a time, no backtracking" presentation
# TODO: export of submission history?
import base64
import datetime
import hashlib
import io
import itertools
import json
from collections import namedtuple, defaultdict
from importlib import import_module
from typing import Optional, Tuple, List, Iterable, Any, Dict

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.backends.db import SessionStore as DatabaseSessionStore
from django.core.checks import Error
from django.core.files import File
from django.db import models, transaction
from django.db.models import Max
from django.http import HttpRequest
from django.shortcuts import resolve_url
from django.utils.functional import cached_property
from django.utils.safestring import SafeText
from ipware import get_client_ip

from coredata.models import Member, CourseOffering
from courselib.conditional_save import ConditionalSaveMixin
from courselib.json_fields import JSONField, config_property
from courselib.markup import markup_to_html
from courselib.storage import UploadedFileStorage, upload_path
from grades.models import Activity, NumericActivity, NumericGrade
from marking.models import ActivityComponent, ActivityComponentMark, StudentActivityMark
from quizzes import DEFAULT_QUIZ_MARKUP
from quizzes.types.file import FileAnswer
from quizzes.types.mc import MultipleChoice, MultipleChoiceMultiple
from quizzes.types.text import ShortAnswer, LongAnswer, FormattedAnswer, NumericAnswer, CodeAnswer

QUESTION_TYPE_CHOICES = [
    ('MC', 'Multiple Choice'),
    ('MCM', 'Multiple Choice (multiple answer)'),
    ('SHOR', 'Short Answer'),
    ('LONG', 'Long Answer'),
    ('FMT', 'Long Answer with formatting'),
    ('CODE', 'Code Entry with syntax highlighting'),
    ('NUM', 'Numeric Answer'),
    ('FILE', 'File Upload'),
]

QUESTION_HELPER_CLASSES = {
    'MC': MultipleChoice,
    'MCM': MultipleChoiceMultiple,
    'SHOR': ShortAnswer,
    'LONG': LongAnswer,
    'FMT': FormattedAnswer,
    'CODE': CodeAnswer,
    'NUM': NumericAnswer,
    'FILE': FileAnswer,
}

STATUS_CHOICES = [
    ('V', 'Visible'),
    ('D', 'Deleted'),
]

REVIEW_CHOICES = [
    ('none', 'may not review quizzes'),
    ('marks', 'may review marks, comments, and review notes; not the questions or their answers'),
    ('answers', 'may review their answers, marks, comments, and review notes; not the questions'),
    ('all', 'may review questions, their answers, marks, comments, and review notes'),
]


class MarkingNotConfiguredError(ValueError):
    pass


def string_hash(s: str, n_bytes: int = 8):
    """
    Create an n_bytes byte integer hash of the string
    """
    h = hashlib.sha256(s.encode('utf-8'))
    return int.from_bytes(h.digest()[:n_bytes], byteorder='big', signed=False)


class Randomizer(object):
    """
    A linear congruential generator (~= pseudorandom number generator). Custom implementation to ensure we can recreate
    a sequence of choices from a seed, regardless of Python's random implementation, etc.
    """

    # ANSI C parameters from
    # https://en.wikipedia.org/wiki/Linear_congruential_generator#Parameters_in_common_use
    def __init__(self, seed_str: str):
        seed = string_hash(seed_str, 7)
        self.m = 2 ** 31
        self.a = 1103515245
        self.c = 12345
        self.x = seed % self.m

    def next(self, n: Optional[int] = None):
        """
        Return the next random integer (optionally, mod n).
        """
        x = (self.a * self.x + self.c) % self.m
        self.x = x
        if n:
            return (x >> 16) % n
        else:
            return x >> 16

    def permute(self, lst: List[Any]) -> List[Any]:
        """
        Return a permuted copy of the list
        """
        result = []
        lst = lst.copy()
        while lst:
            elt = lst.pop(self.next(len(lst)))
            result.append(elt)
        return result


HONOUR_CODE_DEFAULT = '''
In taking this exam you will be required to agree to an honour code statement that affirms your willingness to abide with the course policies. These policies may be adjusted as per your instructor’s discretion, but selecting YES here affirms that you are abiding by the honour code agreement of your course.

I understand that the following activities are prohibited and will be considered cheating. I agree that I will not participate in any of the following activities:
* Looking at or copying from another student’s exam or materials while writing the exam.
* Conferring with other students regarding the exam.
* Having someone else take the exam in your place.
* Storing, receiving, and/or accessing course subject matter in a calculator, pager, cellular telephone, computer, or other electronic device that can be used during an exam period without instructor authorization.
* Distributing the exam materials in any way.
* Using lecture notes, textbooks, learning aids, or electronic devices during an exam when prohibited.

The honour code is an undertaking for students to abide by both individually and collectively. You should do your share and take an active part in seeing to it that you, as well as the peers in your course uphold both the spirit and letter of the honour code.
'''.strip()


class Quiz(models.Model):
    class QuizStatusManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().select_related('activity', 'activity__offering').filter(status='V')

    activity = models.OneToOneField(Activity, on_delete=models.PROTECT)
    start = models.DateTimeField(
        help_text='Quiz will be visible to students after this time. Time format: HH:MM:SS, 24-hour time')
    end = models.DateTimeField(
        help_text='Quiz will be invisible to students and unsubmittable after this time. Time format: HH:MM:SS, 24-hour time')
    status = models.CharField(max_length=1, null=False, blank=False, default='V', choices=STATUS_CHOICES)
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:
    # .config['grace']: length of grace period at the end of the exam (in seconds)
    # .config['intro']: introductory text for the quiz
    # .config['markup']: markup language used: see courselib/markup.py
    # .config['math']: intro uses MathJax? (boolean)
    # .config['secret']: the "secret" used to seed the randomization for this quiz (integer)
    # .config['honour_code']: do we make the student agree to the honour code for this quiz? (boolean)
    # .config['photos']: do we capture verification images for this quiz? (boolean)
    # .config['reviewable']: defunct. Now maps to True -> .review == 'all'; False -> .review == 'none'
    # .config['review']: can students review, and what can they see? REVIEW_CHOICES gives options.
    # .config['honour_code_text']: markup of the honour code
    # .config['honour_code_markup']: honour code markup language
    # .config['honour_code_math']: honour code uses MathJax? (boolean)

    grace = config_property('grace', default=300)
    intro = config_property('intro', default='')
    markup = config_property('markup', default=DEFAULT_QUIZ_MARKUP)
    math = config_property('math', default=False)
    secret = config_property('secret', default='not a secret')
    honour_code = config_property('honour_code', default=True)
    honour_code_text = config_property('honour_code_text', default=HONOUR_CODE_DEFAULT)
    honour_code_markup = config_property('honour_code_markup', default=DEFAULT_QUIZ_MARKUP)
    honour_code_math = config_property('honour_code_math', default=False)
    photos = config_property('photos', default=False)
    #review = config_property('reviewable', default='none')  # special-cased below

    # Special handling to honour .config['reviewable'] if it was set before .config['review'] existed.
    def _review_get(self):
        if 'review' in self.config:
            return self.config['review']
        elif 'reviewable' in self.config:
            return 'all' if self.config['reviewable'] else 'none'
        else:
            return 'none'

    def _review_set(self, val):
        if 'reviewable' in self.config:
            del self.config['reviewable']
        self.config['review'] = val

    review = property(_review_get, _review_set)

    # .config fields allowed in the JSON import
    ALLOWED_IMPORT_CONFIG = {'grace', 'honour_code', 'photos', 'reviewable', 'review'}

    class Meta:
        verbose_name_plural = 'Quizzes'

    objects = QuizStatusManager()

    def get_absolute_url(self):
        return resolve_url('offering:quiz:index', course_slug=self.activity.offering.slug,
                           activity_slug=self.activity.slug)

    def save(self, *args, **kwargs):
        res = super().save(*args, **kwargs)
        if 'secret' not in self.config:
            # Ensure we are saved (so self.id is filled), and if the secret isn't there, fill it in.
            self.config['secret'] = string_hash(settings.SECRET_KEY) + self.id
            super().save(*args, **kwargs)
        return res

    def get_start_end(self, member: Optional[Member]) -> Tuple[datetime.datetime, datetime.datetime]:
        """
        Get the start and end times for this quiz.

        The start/end may have been overridden by the instructor for this student, but default to .start and .end if not
        """
        if not member:
            # in the generic case, use the defaults
            return self.start, self.end

        special_case = TimeSpecialCase.objects.filter(quiz=self, student=member).first()
        if not special_case:
            # no special case for this student
            return self.start, self.end
        else:
            # student has a special case
            return special_case.start, special_case.end

    def get_starts_ends(self, members: Iterable[Member]) -> Dict[Member, Tuple[datetime.datetime, datetime.datetime]]:
        """
        Get the start and end times for this quiz for each member.
        """
        special_cases = TimeSpecialCase.objects.filter(quiz=self, student__in=members).select_related('student')
        sc_lookup = {sc.student: sc for sc in special_cases}
        # stub so we can always get a TimeSpecialCase in the comprehension below
        default = TimeSpecialCase(start=self.start, end=self.end)
        return {m: (sc_lookup.get(m, default).start, sc_lookup.get(m, default).end) for m in members}

    def ongoing(self, member: Optional[Member] = None) -> bool:
        """
        Is the quiz currently in-progress?
        """
        start, end = self.get_start_end(member=member)
        if not start or not end:
            # newly created with start and end not yet filled
            return False
        now = datetime.datetime.now()
        return start <= now <= end

    def completed(self, member: Optional[Member] = None) -> bool:
        """
        Is the quiz over?
        """
        _, end = self.get_start_end(member=member)
        if not end:
            # newly created with end not yet filled
            return False
        now = datetime.datetime.now()
        return now > end

    def intro_html(self) -> SafeText:
        return markup_to_html(self.intro, markuplang=self.markup, math=self.math, hidden_llm=True)

    def honour_code_html(self) -> SafeText:
        return markup_to_html(self.honour_code_text, markuplang=self.honour_code_markup, math=self.honour_code_math, hidden_llm=True)

    def random_generator(self, seed: str) -> Randomizer:
        """
        Return a "random" value generator with given seed, which must be deterministic so we can reproduce the values.
        """
        seed_str = str(self.secret) + '--' + seed
        return Randomizer(seed_str)

    @transaction.atomic
    def configure_marking(self, delete_others=True):
        """
        Configure the rubric-based marking to be quiz marks.
        """
        if not self.activity.quiz_marking():
            self.activity.set_quiz_marking(True)
            self.activity.save()

        num_activity = NumericActivity.objects.get(id=self.activity_id)
        total = 0

        all_components = ActivityComponent.objects.filter(numeric_activity=num_activity)
        questions = self.question_set.all()
        i = 0

        for i, q in enumerate(questions):
            existing_comp = [c for c in all_components if c.config.get('quiz-question-id', None) == q.id]
            if existing_comp:
                component = existing_comp[0]
            else:
                component = ActivityComponent(numeric_activity=num_activity)

            component.position = i + 1
            component.max_mark = q.points
            component.title = 'Question #%i' % (i + 1,)
            # component.description = '' # if instructor has entered a description, let it stand
            component.deleted = False
            component.config['quiz-question-id'] = q.id
            component.save()

            component.used = True
            total += q.points

        pos = i + 2
        for c in all_components:
            if hasattr(c, 'used') and c.used:
                continue
            else:
                if delete_others or c.config.get('quiz-question-id', None):
                    # delete other components if requested, and always delete other quiz-created components
                    c.deleted = True
                else:
                    # or reorder to the bottom if not
                    c.position = pos
                    pos += 1
                    if not c.deleted:
                        total += c.max_mark
                c.save()

        old_max = num_activity.max_grade
        if old_max != total:
            num_activity.max_grade = total
            num_activity.save()

    def activitycomponents_by_question(self) -> Dict['Question', ActivityComponent]:
        """
        Build dict to map Question to corresponding ActivityComponent in marking.
        """
        questions = self.question_set.all()
        components = ActivityComponent.objects.filter(numeric_activity_id=self.activity_id, deleted=False)
        question_lookup = {q.id: q for q in questions}
        component_lookup = {}

        for c in components:
            if 'quiz-question-id' in c.config and c.config['quiz-question-id'] in question_lookup:
                q = question_lookup[c.config['quiz-question-id']]
                component_lookup[q] = c

        return component_lookup

    @transaction.atomic()
    def automark_all(self, user: User) -> int:
        """
        Fill in marking for any QuestionVersions that support it. Return number marked.
        """
        versions = QuestionVersion.objects.filter(question__quiz=self, question__status='V').select_related('question')
        activity_components = self.activitycomponents_by_question()
        member_component_results = []  # : List[Tuple[Member, ActivityComponentMark]]
        for v in versions:
            member_component_results.extend(
                v.automark_all(activity_components=activity_components)
            )

        # Now the ugly work: combine the just-automarked components with any existing manual marking, and save...

        old_sam_lookup = {  # dict to find old StudentActivityMarks
            sam.numeric_grade.member: sam
            for sam
            in StudentActivityMark.objects.filter(activity=self.activity)
                .order_by('created_at')
                .select_related('numeric_grade__member')
                .prefetch_related('activitycomponentmark_set')
        }

        # dict to find old ActivityComponentMarks
        old_acm_by_component_id = defaultdict(dict)  # : Dict[int, Dict[Member, ActivityComponentMark]]
        old_sam = StudentActivityMark.objects.filter(activity=self.activity).order_by('created_at') \
            .select_related('numeric_grade__member').prefetch_related('activitycomponentmark_set')
        for sam in old_sam:
            for acm in sam.activitycomponentmark_set.all():
                old_acm_by_component_id[acm.activity_component_id][sam.numeric_grade.member] = acm

        numeric_grade_lookup = {  # dict to find existing NumericGrades
            ng.member: ng
            for ng
            in NumericGrade.objects.filter(activity=self.activity).select_related('member')
        }
        all_components = set(ActivityComponent.objects.filter(numeric_activity_id=self.activity_id, deleted=False))

        member_component_results.sort(key=lambda pair: pair[0].id)  # ... get Members grouped together
        n_marked = 0
        for member, member_acms in itertools.groupby(member_component_results, lambda pair: pair[0]):
            # Get a NumericGrade to work with
            try:
                ngrade = numeric_grade_lookup[member]
            except KeyError:
                ngrade = NumericGrade(activity_id=self.activity_id, member=member, flag='NOGR')
                ngrade.save(newsitem=False, entered_by=None, is_temporary=True)

            # Create ActivityMark to save under
            am = StudentActivityMark(numeric_grade=ngrade, activity_id=self.activity_id, created_by=user.username)
            old_am = old_sam_lookup.get(member)
            if old_am:
                am.overall_comment = old_am.overall_comment
                am.late_penalty = old_am.late_penalty
                am.mark_adjustment = old_am.mark_adjustment
                am.mark_adjustment_reason = old_am.mark_adjustment_reason
            am.save()

            # Find/create ActivityComponentMarks for each component
            auto_acm_lookup = {acm.activity_component: acm for _, acm in member_acms}
            any_missing = False
            acms = []
            for c in all_components:
                # For each ActivityComponent, find one of
                # (1) just-auto-marked ActivityComponentMark,
                # (2) ActivityComponentMark from previous manual marking,
                # (3) nothing.
                if c in auto_acm_lookup:  # (1)
                    acm = auto_acm_lookup[c]
                    acm.activity_mark = am
                    n_marked += 1
                elif c.id in old_acm_by_component_id and member in old_acm_by_component_id[c.id]:  # (2)
                    old_acm = old_acm_by_component_id[c.id][member]
                    acm = ActivityComponentMark(activity_mark=am, activity_component=c, value=old_acm.value, comment=old_acm.comment)
                else:  # (3)
                    acm = ActivityComponentMark(activity_mark=am, activity_component=c, value=None, comment=None)
                    any_missing = True

                acm.save()
                acms.append(acm)

            if not any_missing:
                total = am.calculated_mark(acms)
                ngrade.value = total
                ngrade.flag = 'GRAD'
                am.mark = total
            else:
                ngrade.value = 0
                ngrade.flag = 'NOGR'
                am.mark = None

            ngrade.save(newsitem=False, entered_by=user.username)
            am.save()

        return n_marked

    def export(self) -> Dict[str, Any]:
        config = {
            'grace': self.grace,
            'honour_code': self.honour_code,
            'photos': self.photos,
            'review': self.review,
        }
        intro = [self.intro, self.markup, self.math]
        questions = [q.export() for q in self.question_set.all()]
        return {
            'config': config,
            'intro': intro,
            'questions': questions,
        }


class Question(models.Model, ConditionalSaveMixin):
    class QuestionStatusManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().select_related('quiz').prefetch_related('versions').filter(status='V')

    quiz = models.ForeignKey(Quiz, null=False, blank=False, on_delete=models.PROTECT)
    type = models.CharField(max_length=4, null=False, blank=False, choices=QUESTION_TYPE_CHOICES)
    status = models.CharField(max_length=1, null=False, blank=False, default='V', choices=STATUS_CHOICES)
    order = models.PositiveSmallIntegerField(null=False, blank=False)
    config = JSONField(null=False, blank=False, default=dict)
    # .config['points']: points the question is worth (positive integer)

    points = config_property('points', default=1)

    class Meta:
        ordering = ['order']

    objects = QuestionStatusManager()
    all_objects = models.Manager()

    def get_absolute_url(self):
        return resolve_url('offering:quiz:index', course_slug=self.quiz.activity.offering.slug,
                           activity_slug=self.quiz.activity.slug) + '#' + self.ident()

    def ident(self):
        """
        Unique identifier that can be used as a input name or HTML id value.
        """
        return 'q-%i' % (self.id,)

    def set_order(self):
        """
        If the question has no .order, set the .order value to the current max + 1
        """
        if self.order is not None:
            return

        current_max = Question.objects.filter(quiz=self.quiz).aggregate(Max('order'))['order__max']
        if not current_max:
            self.order = 1
        else:
            self.order = current_max + 1

    def export(self) -> Dict[str, Any]:
        return {
            'points': self.points,
            'type': self.type,
            'versions': [v.export() for v in self.versions.all()]
        }


class QuestionVersion(models.Model):
    class VersionStatusManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().select_related('question').filter(status='V')

    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name='versions')
    status = models.CharField(max_length=1, null=False, blank=False, default='V', choices=STATUS_CHOICES)
    created_at = models.DateTimeField(default=datetime.datetime.now, null=False, blank=False)  # used for ordering
    config = JSONField(null=False, blank=False, default=dict)
    # .config['text']: question as (text, markup, math:bool)
    # .config['marking']: marking notes as (text, markup, math:bool)
    # .config['review']: review notes as (text, markup, math:bool)
    # others as set by the .question.type (and corresponding QuestionType)

    text = config_property('text', default=('', DEFAULT_QUIZ_MARKUP, False))
    marking = config_property('marking', default=('', DEFAULT_QUIZ_MARKUP, False))
    review = config_property('review', default=('', DEFAULT_QUIZ_MARKUP, False))

    objects = VersionStatusManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['question', 'created_at', 'id']

    def helper(self, question: Optional['Question'] = None):
        return QUESTION_HELPER_CLASSES[self.question.type](version=self, question=question)

    def export(self) -> Dict[str, Any]:
        return self.config

    @classmethod
    def select(cls, quiz: Quiz, questions: Iterable[Question], student: Optional[Member],
               answers: Optional[Iterable['QuestionAnswer']]) -> List['QuestionVersion']:
        """
        Build a (reproducibly-random) set of question versions. Honour the versions already answered, if instructor
        has been fiddling with questions during the quiz.
        """
        assert (student is None and answers is None) or (
                    student is not None and answers is not None), 'must give current answers if student is known.'
        if student:
            rand = quiz.random_generator(str(student.id))

        all_versions = QuestionVersion.objects.filter(question__in=questions)
        version_lookup = {
            q_id: list(vs)
            for q_id, vs in itertools.groupby(all_versions, key=lambda v: v.question_id)
        }
        if answers is not None:
            answers_lookup = {
                a.question_id: a
                for a in answers
            }

        versions = []
        for q in questions:
            vs = version_lookup[q.id]
            if student:
                # student: choose randomly unless they have already answered a version
                # We need to call rand.next() here to update the state of the LCG, even if we have something
                # in answers_lookup
                n = rand.next(len(vs))

                if q.id in answers_lookup:
                    ans = answers_lookup[q.id]
                    v = ans.question_version
                    try:
                        v.choice = vs.index(v) + 1
                    except ValueError:
                        # Happens if a student answers a version, but then the instructor deletes it. Hopefully never.
                        v.choice = 0
                else:
                    v = vs[n]
                    v.choice = n + 1

            else:
                # instructor preview: choose the first
                v = vs[0]
                v.choice = 1

            v.n_versions = len(vs)
            versions.append(v)

        return versions

    def question_html(self) -> SafeText:
        """
        Markup for the question itself
        """
        helper = self.helper()
        return helper.question_html()

    def question_preview_html(self) -> SafeText:
        """
        Markup for an instructor's preview of the question (e.g. question + MC options)
        """
        helper = self.helper()
        return helper.question_preview_html()

    def entry_field(self, student: Optional[Member], questionanswer: 'QuestionAnswer' = None):
        helper = self.helper()
        if questionanswer:
            assert questionanswer.question_version_id == self.id
        return helper.get_entry_field(questionanswer=questionanswer, student=student)

    def entry_head_html(self) -> SafeText:
        """
        Markup this version needs inserted into the <head> on the question page.
        """
        helper = self.helper()
        return helper.entry_head_html()

    def marking_html(self) -> SafeText:
        text, markup, math = self.marking
        return markup_to_html(text, markup, math=math, hidden_llm=True)

    def review_html(self) -> SafeText:
        text, markup, math = self.review
        return markup_to_html(text, markup, math=math, hidden_llm=True)

    def automark_all(self, activity_components: Dict['Question', ActivityComponent]) -> Iterable[Tuple[Member, ActivityComponentMark]]:
        """
        Automark everything for this version, if possible. Return Student/ActivityComponentMark pairs that need to be saved with an appropriate StudentActivityMark
        """
        helper = self.helper(question=self.question)
        if not helper.auto_markable:
            # This helper can't do automarking, so don't try.
            return

        try:
            component = activity_components[self.question]
        except KeyError:
            raise MarkingNotConfiguredError()

        answers = QuestionAnswer.objects.filter(question_version=self).select_related('question', 'student')
        for a in answers:
            mark = helper.automark(a)
            if mark is None:
                # helper is allowed to throw up its hands and return None if auto-marking not possible
                continue

            # We have a mark and comment: create a ActivityComponentMark for it
            points, comment = mark
            member = a.student
            comp_mark = ActivityComponentMark(activity_component=component, value=points, comment=comment)
            yield member, comp_mark


def file_upload_to(instance, filename):
    return upload_path(instance.question.quiz.activity.offering.slug, '_quizzes', filename)


class QuestionAnswer(models.Model):
    class AnswerStatusManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().select_related('question', 'question_version').filter(question__status='V')

    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    question_version = models.ForeignKey(QuestionVersion, on_delete=models.PROTECT)
    # Technically .question is redundant with .question_version.question, but keeping it for convenience
    # and the unique_together.
    student = models.ForeignKey(Member, on_delete=models.PROTECT)
    modified_at = models.DateTimeField(default=datetime.datetime.now, null=False, blank=False)
    # format of .answer determined by the corresponding QuestionHelper
    answer = JSONField(null=False, blank=False, default=dict)
    # .file used for file upload question types; null otherwise
    file = models.FileField(blank=True, null=True, storage=UploadedFileStorage, upload_to=file_upload_to,
                            max_length=500)

    class Meta:
        unique_together = [['question_version', 'student']]

    objects = AnswerStatusManager()

    def save(self, *args, **kwargs):
        assert self.question_id == self.question_version.question_id  # ensure denormalized field stays consistent

        saving_file = False
        if '_file' in self.answer:
            if self.answer['_file'] is None:
                # keep current .file
                pass
            elif self.answer['_file'] is False:
                # user requested "clear"
                self.file = None
            else:
                # actually a file
                self.file = self.answer['_file']
                saving_file = True

            del self.answer['_file']

        if saving_file:
            # Inject the true save path into the .answer. Requires a double .save()
            super().save(*args, **kwargs)
            fn = self.file.name
            self.answer['filepath'] = fn

        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return resolve_url('offering:quiz:view_submission', course_slug=self.question.quiz.activity.offering.slug,
                           activity_slug=self.question.quiz.activity.slug,
                           userid=self.student.person.userid_or_emplid()) + '#' + self.question.ident()

    def answer_html(self) -> SafeText:
        helper = self.question_version.helper()
        return helper.to_html(self)


def capture_upload_to(instance, filename):
    return upload_path(instance.quiz.activity.offering.slug, '_quiz_photos', filename)


class QuizSubmission(models.Model):
    """
    Model to log everything we can think of about a quiz submission, for possible later analysis.
    """
    quiz = models.ForeignKey(Quiz, null=False, blank=False, on_delete=models.PROTECT)
    student = models.ForeignKey(Member, null=False, blank=False, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=datetime.datetime.now, null=False, blank=False)
    ip_address = models.GenericIPAddressField(null=False, blank=False)
    capture = models.FileField(null=True, blank=True, storage=UploadedFileStorage, upload_to=capture_upload_to,
                               max_length=500)
    config = JSONField(null=False, blank=False, default=dict)  # additional data about the submission:

    # .config['answers']: list of answers submitted (where changed from prev submission),
    #     as [(QuestionVersion.id, Answer.id, Answer.answer)]
    # .config['user_agent']: HTTP User-Agent header from submission
    # .config['session']: the session_key from the submission
    # .config['csrf_token']: the CSRF token being used for the submission
    # .config['fingerprint']: browser fingerprint provided by fingerprintjs2
    # .config['honour_code']: did student agree to the honour code?
    # .config['autosave']: was this an auto-save?

    @classmethod
    def create(cls, request: HttpRequest, quiz: Quiz, student: Member, answers: List[QuestionAnswer],
               commit: bool = True, autosave: bool = False) -> 'QuizSubmission':
        qs = cls(quiz=quiz, student=student)
        ip_addr, _ = get_client_ip(request)
        qs.ip_address = ip_addr
        qs.config['answers'] = [(a.question_version_id, a.id, a.answer) for a in answers]
        qs.config['session'] = request.session.session_key
        qs.config['csrf_token'] = request.META.get('CSRF_COOKIE')
        qs.config['user_agent'] = request.META.get('HTTP_USER_AGENT')
        qs.config['honour_code'] = request.POST.get('honour-code', None)
        qs.config['autosave'] = autosave
        try:
            qs.config['fingerprint'] = json.loads(request.POST['fingerprint'])
        except KeyError:
            qs.config['fingerprint'] = 'missing'
        except json.JSONDecodeError:
            qs.config['fingerprint'] = 'json-error'

        try:
            capture_data_uri = request.POST['photo-capture']
            # data: parsing from https://stackoverflow.com/a/33870677
            header, encoded = capture_data_uri.split(",", 1)
            capture = base64.b64decode(encoded)
            f = File(file=io.BytesIO(capture), name='%i.png' % (student.id,))
            qs.capture = f
        except (KeyError, ValueError):
            # if there's a problem, let it go.
            qs.capture = None

        if commit:
            qs.save()
        return qs

    @classmethod
    def check(cls, **kwargs):
        """
        We use .session_key and CSRF_COOKIE above: check that they will be there, and fail fast if not.
        """
        errors = super().check(**kwargs)

        # Ensure we are using the database session store. (Other SessionStores may also have .session_key?)
        engine = import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore
        if not issubclass(store, DatabaseSessionStore):
            errors.append(Error(
                "Quiz logging uses request.session.session_key, which likely implies "
                "SESSION_ENGINE = 'django.contrib.sessions.backends.db' in settings."
            ))

        if 'django.middleware.csrf.CsrfViewMiddleware' not in settings.MIDDLEWARE:
            errors.append(Error(
                "CsrfViewMiddleware is not enabled in settings: quiz logging uses CSRF_COOKIE and will fail without "
                "CSRF checking enabled. Also it should be enabled in general."
            ))

        return errors

    AnswerData = namedtuple('AnswerData', ['question', 'n', 'answer', 'answer_html'])

    def annotate_questions(self, questions: Iterable[Question], versions: Iterable[QuestionVersion]) -> None:
        """
        Annotate this object to combine .config['answers'] and questions for efficient display later.
        """
        answers = self.config['answers']
        question_lookup = {q.id: (q, i + 1) for i, q in enumerate(questions)}
        version_lookup = {v.id: v for v in versions}
        answer_data = []
        for version_id, answer_id, answer in answers:
            version = version_lookup[version_id]
            question, n = question_lookup[version.question_id]
            # temporarily reconstruct the QuestionAnswer so we can generate HTML
            qa = QuestionAnswer(id=answer_id, question=question, question_version=version, student=self.student,
                                modified_at=self.created_at, answer=answer)
            answer_html = version.helper(question=question).to_html(qa)
            data = QuizSubmission.AnswerData(question=question, n=n, answer=answer, answer_html=answer_html)
            answer_data.append(data)

        self.answer_data = answer_data

    @cached_property
    def session_fingerprint(self) -> str:
        """
        Return a hash of what we know about the user's session on submission.
        We could incorporate csrf_token here, but are we *sure* it only changes on login?
        """
        ident = self.config['session']  # + '--' + self.config['csrf_token']
        return '%08x' % (string_hash(ident, 4),)

    @cached_property
    def browser_fingerprint(self) -> str:
        """
        Return a hash of what we know about the user's browser on submission.
        """
        # including user_agent is generally redundant, but not if the fingerprinting fails for some reason
        ident = self.config['user_agent'] + '--' + json.dumps(self.config['fingerprint'])
        return '%08x' % (string_hash(ident, 4),)


class TimeSpecialCase(models.Model):
    """
    Model to represent quiz start/end times that are unique to one student, to allow makeup quizzes, accessibility
    accommodations, etc.
    """
    quiz = models.ForeignKey(Quiz, null=False, blank=False, on_delete=models.PROTECT)
    student = models.ForeignKey(Member, on_delete=models.PROTECT)
    start = models.DateTimeField(
        help_text='Quiz will be visible to the student after this time. Time format: HH:MM:SS, 24-hour time')
    end = models.DateTimeField(
        help_text='Quiz will be invisible to the student and unsubmittable after this time. Time format: HH:MM:SS, 24-hour time')
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:

    class Meta:
        unique_together = [['quiz', 'student']]


def copy_quizzes(old_to_new: Dict[int, int]) -> None:
    """
    Copy quiz setup from one offering to another.
    old_to_new is a map of all old_offering.activity.id -> new_offering.activity.id values.
    """
    relevant_activities = Activity.objects.filter(id__in=old_to_new.values())
    activity_map = {a.id: a for a in relevant_activities}
    quizzes = Quiz.objects.filter(activity__id__in=old_to_new.keys()).select_related('activity__offering__semester')
    for old_q in quizzes:
        old_a = old_q.activity
        old_o = old_a.offering
        new_a = activity_map[old_to_new[old_a.id]]
        new_o = new_a.offering
        old_questions = Question.objects.filter(quiz=old_q)

        new_q = old_q
        new_q.id = None
        new_q.pk = None
        new_q.activity = new_a
        del new_q.config['secret']  # force new secret generation on .save()

        # map .start and .end to new semester
        week, wkday = old_o.semester.week_weekday(old_q.start)
        new_q.start = new_o.semester.duedate(week, wkday, old_q.start)
        week, wkday = old_o.semester.week_weekday(old_q.end)
        new_q.end = new_o.semester.duedate(week, wkday, old_q.end)

        new_q.save()

        for old_quest in old_questions:
            old_versions = QuestionVersion.objects.filter(question=old_quest)
            new_quest = old_quest
            new_quest.id = None
            new_quest.pk = None
            new_quest.quiz = new_q
            new_quest.save()

            for old_v in old_versions:
                new_v = old_v
                new_v.id = None
                new_v.pk = None
                new_v.question = new_quest
                new_v.save()

