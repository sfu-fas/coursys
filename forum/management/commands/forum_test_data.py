import datetime
import random

from django.core.management.base import BaseCommand
from django.conf import settings

from coredata.models import CourseOffering, Member
from courselib.testing import TEST_COURSE_SLUG
from forum.models import Forum, Post, Thread, Reply, Reaction, Identity


class Command(BaseCommand):
    help = 'Build some test data for development.'

    def add_arguments(self, parser):
        parser.add_argument('--threads', type=int, default=30)
        parser.add_argument('--replies', type=int, default=30)

    def handle(self, *args, **options):
        assert not settings.DO_IMPORTING_HERE
        assert settings.DEPLOY_MODE != 'production'

        o = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        f, _ = Forum.objects.get_or_create(offering=o)
        f.enabled = True
        f.identity = 'ANON'
        f.save()

        instr = Member.objects.get(offering=o, person__userid='ggbaker')
        students = list(Member.objects.filter(offering=o, role='STUD'))

        ident = Identity.for_member(instr)
        ident.digest_frequency = 1
        ident.avatar_type = 'gravatar'
        ident.anon_avatar_type = 'robohash'
        ident.save()

        for i in range(options['threads'], 0, -1):
            asker = random.choice(students)
            ptype = random.choice(['QUES', 'QUES', 'DISC'])
            time = datetime.datetime.now() - datetime.timedelta(hours=i)
            p = Post(offering=o, author=asker, type=ptype, created_at=time, modified_at=time)
            if ptype == 'QUES':
                thread = Thread(title='A Question', post=p)
                p.content = "Can I or not?\n\nI'm not really sure."
            else:
                thread = Thread(title="Let's discuss", post=p)
                p.content = "Do we all agree?"
            p.markup = 'markdown'
            p.identity = random.choice(['INST', 'ANON', 'NAME'])
            thread.save()

            p = Post(offering=o, author=random.choice(students), created_at=time, modified_at=time)
            p.content = 'Yeah, probably.'
            p.markup = 'markdown'
            p.identity = random.choice(['INST', 'ANON', 'NAME'])
            reply = Reply(thread=thread, parent=thread.post, post=p)
            reply.save()

            if random.random() < 0.4:
                # asker thumbs-up on student reply
                react = Reaction(member=asker, post=p, reaction='UP')
                react.save()

            if random.random() < 0.4:
                # instructor reply
                p = Post(offering=o, author=instr)
                p.content = 'Yes.'
                p.markup = 'markdown'
                p.identity = 'NAME'
                reply = Reply(thread=thread, parent=thread.post, post=p)
                reply.save()

            thread.post.update_status(commit=True)

        # the last thread also get a bunch of replies
        for _ in range(options['replies']):
            p = Post(offering=o, author=random.choice(students))
            p.content = 'Another reply.'
            p.markup = 'markdown'
            p.identity = random.choice(['INST', 'ANON', 'NAME'])
            reply = Reply(thread=thread, parent=thread.post, post=p)
            reply.save()
