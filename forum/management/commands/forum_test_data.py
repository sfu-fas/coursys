from django.core.management.base import BaseCommand
from django.conf import settings

from coredata.models import CourseOffering, Member
from courselib.testing import TEST_COURSE_SLUG
from forum.models import Forum, Post, Thread, Reply


class Command(BaseCommand):
    help = 'Build some test data for development.'

    def handle(self, *args, **options):
        assert not settings.DO_IMPORTING_HERE
        assert settings.DEPLOY_MODE != 'production'

        o = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        f, _ = Forum.objects.get_or_create(offering=o)
        f.enabled = True
        f.identity = 'INST'
        f.save()

        instr = Member.objects.get(offering=o, person__userid='ggbaker')
        student = Member.objects.get(offering=o, person__userid='0aaa0')

        p = Post(offering=o, author=student, type='QUES')
        p.content = "Can I or not?\n\nI'm not really sure."
        p.markup = 'markdown'
        p.identity = 'INST'
        t = Thread(title='A Question', post=p)
        t.save()
        self.thread = t

        p = Post(offering=o, author=instr)
        p.content = 'Yeah, probably.'
        p.markup = 'markdown'
        p.identity = 'NAME'
        r = Reply(thread=t, parent=t.post, post=p)
        r.save()
        self.reply = r
