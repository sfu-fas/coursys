from django.test import TestCase
from django.db.utils import IntegrityError
from models import FormGroup
from coredata.models import Person, Unit

class ModelTests(TestCase):
    fixtures = ['test_data']
    #def setUp(self):

    def test_FormGroup(self):
        groupName = "admins"
        u1 = Unit.objects.get(label="COMP")
        u2 = Unit.objects.get(label="ENG")
        # Test saving one form group
        fg = FormGroup(name=groupName, unit=u1)
        fg.save()
        self.assertEqual(fg.name, groupName)
        # now try adding another fromgroup in the same name with the same unit
        # should throw an db integrity exception
        fg2 = FormGroup(name=groupName, unit=u1)
        self.assertRaises(IntegrityError, fg2.save)
        # now add a formgroup with the same name into a different unit
        fg2 = FormGroup(name=groupName, unit=u2)
        fg2.save()
        self.assertEqual(fg2.name, groupName)
        self.assertEqual(fg2.unit, u2)
        # add some people to the fg
        p1 = Person.objects.get(userid="ggbaker")
        p2 = Person.objects.get(userid="dzhao")
        fg.members.add(p1)
        fg.members.add(p2)
        self.assertEqual(len(fg.members.all()), 2)

