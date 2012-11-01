from django.test import TestCase
from django.db.utils import IntegrityError
from onlineforms.models import FormGroup, Form, Sheet, Field
from coredata.models import Person, Unit

class ModelTests(TestCase):
    fixtures = ['test_data']
    def setUp(self):
        self.unit = Unit.objects.get(label="COMP")

    def test_FormGroup(self):
        return
        groupName = "admins_test"
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

    def test_coherence_mixin(self):
        """
        Make sure .active and .original are getting manipulated correctly.
        """
        return
        # create new form
        form = Form(title="Test Form", unit=self.unit, owner=FormGroup.objects.all()[0])
        form.save()
        orig_form_id = form.id
        self.assertEqual(form.active, True)
        self.assertEqual(form.original_id, orig_form_id)
        
        # make a clone and save
        form = form.clone()
        form.save()

        # check the state of the forms
        self.assertEqual(form.active, True)
        self.assertEqual(form.original_id, orig_form_id)
        self.assertNotEqual(form.id, orig_form_id)
        orig_form = Form.objects.get(id=orig_form_id)
        self.assertEqual(orig_form.original_id, orig_form_id)
        self.assertEqual(orig_form.active, False)

        
        # create a sheet
        sheet = Sheet(form=form, title="Test Sheet", is_initial=True)
        sheet.save()
        orig_sheet_id = sheet.id
        self.assertEqual(sheet.active, True)
        self.assertEqual(sheet.original_id, orig_sheet_id)
        # fake a same-original sheet on another version of the form
        sheetX = Sheet(form=orig_form, title="Test Sheet", is_initial=True, original=sheet.original)
        sheetX.save()
        
        # make a clone and save
        sheet = sheet.clone()
        sheet.save()
        
        # check the state of the forms
        self.assertEqual(sheet.active, True)
        self.assertEqual(sheet.original_id, orig_sheet_id)
        self.assertNotEqual(sheet.id, orig_sheet_id)
        orig_sheet = Sheet.objects.get(id=orig_sheet_id)
        self.assertEqual(orig_sheet.original_id, orig_sheet_id)
        self.assertEqual(orig_sheet.active, False)
        self.assertEqual(sheetX.active, True) # cousin shouldn't be deactivated, since it's on a different version of the form
        
        
    def test_sheet_copy(self):
        sheet1 = Sheet.objects.get(slug='initial-sheet')
        f1 = Field(label="F1", sheet=sheet1)
        f1.save()
        f2 = Field(label="F2", sheet=sheet1)
        f2.save()
        f3 = Field(label="F3", sheet=sheet1, active=False)
        f3.save()

        self.assertEqual(Field.objects.filter(sheet=sheet1).count(), 3)
        self.assertEqual(Field.objects.filter(sheet=sheet1, active=True).count(), 2)
        
        # copy the sheet and make sure things are okay
        sheet2 = sheet1.safe_save()
        sheet1 = Sheet.objects.get(id=sheet1.id) # get sheet1 again, as changed in the DB
        
        self.assertEqual(sheet1.original, sheet2.original)
        self.assertEqual(sheet1, sheet2.original)
        self.assertTrue(sheet2.active)
        self.assertFalse(sheet1.active)
        self.assertEqual(Field.objects.filter(sheet=sheet1).count(), 3)
        self.assertEqual(Field.objects.filter(sheet=sheet1, active=True).count(), 2)
        self.assertEqual(Field.objects.filter(sheet=sheet2).count(), 2) # inactive isn't copied
        self.assertEqual(Field.objects.filter(sheet=sheet2, active=True).count(), 2)
        
        # copy a field and make sure things are okay
        f3a = Field.objects.filter(sheet=sheet2)[0]
        f3b = f3a.safe_save()
        
        self.assertNotEqual(f3a.sheet, f3b.sheet)
        self.assertEqual(f3a.sheet.form, f3b.sheet.form)
        self.assertEqual(f3a.label, f3b.label)
        self.assertEqual(f3a.original, f3b.original)
        self.assertEqual(Field.objects.filter(sheet=f3b.sheet, active=True).count(), 2)
        
        
        





        
        