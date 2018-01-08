from django.test import TestCase
import django.db.transaction
from django.db.utils import IntegrityError
from django.core.urlresolvers import reverse
from django.forms import Field as DjangoFormsField, Form as DjangoForm

from coredata.models import Person, Unit
from courselib.testing import basic_page_tests, Client

from onlineforms.models import FormGroup, FormGroupMember, Form, Sheet, Field
from onlineforms.models import FormSubmission, SheetSubmission, FieldSubmission, SheetSubmissionSecretUrl
from onlineforms.models import FIELD_TYPE_MODELS


# repeats a string to exactly the length we want
def repeat_to_length(string_to_expand, length):
    return (string_to_expand * ((length / len(string_to_expand)) + 1))[:length]


class ModelTests(TestCase):
    fixtures = ['basedata', 'coredata', 'onlineforms']

    def setUp(self):
        self.unit = Unit.objects.get(label="CMPT")

    def test_FormGroups(self):
        groupName = "admins_test"
        u1 = Unit.objects.get(label="CMPT")
        u2 = Unit.objects.get(label="ENSC")
        # Test saving one form group
        fg = FormGroup(name=groupName, unit=u1)
        fg.save()
        self.assertEqual(fg.name, groupName)
        # now try adding another fromgroup in the same name with the same unit
        # should throw an db integrity exception
        fg2 = FormGroup(name=groupName, unit=u1)
        with self.assertRaises(IntegrityError):
            with django.db.transaction.atomic():
                fg2.save()
        # now add a formgroup with the same name into a different unit
        fg2 = FormGroup(name=groupName, unit=u2)
        fg2.save()
        self.assertEqual(fg2.name, groupName)
        self.assertEqual(fg2.unit, u2)
        # add some people to the fg
        p1 = Person.objects.get(userid="ggbaker")
        p2 = Person.objects.get(userid="dzhao")
        FormGroupMember(person=p1, formgroup=fg).save()
        FormGroupMember(person=p2, formgroup=fg).save()
        self.assertEqual(len(fg.members.all()), 2)

    def test_coherence_mixin(self):
        """
        Make sure .active and .original are getting manipulated correctly.
        """
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
        self.assertEqual(sheetX.active, True)  # cousin shouldn't be deactivated, since it's on a different version of the form

    def test_sheet_copy(self):
        fg = FormGroup.objects.create(name="Admin Test", unit=self.unit)
        form = Form.objects.create(title="Test Form", unit=self.unit, owner=fg)
        sheet1 = Sheet.objects.create(title="Initial Sheet", form=form)
        # create three fields
        Field.objects.create(label="F1", sheet=sheet1)
        Field.objects.create(label="F2", sheet=sheet1)
        Field.objects.create(label="F3", sheet=sheet1, active=False)

        self.assertEqual(Field.objects.filter(sheet=sheet1).count(), 3)
        self.assertEqual(Field.objects.filter(sheet=sheet1, active=True).count(), 2)

        # copy the sheet and make sure things are okay
        sheet2 = sheet1.safe_save()
        sheet1 = Sheet.objects.get(id=sheet1.id)  # get sheet1 again, as changed in the DB

        self.assertEqual(sheet1.original, sheet2.original)
        self.assertEqual(sheet1, sheet2.original)
        self.assertTrue(sheet2.active)
        self.assertFalse(sheet1.active)
        self.assertEqual(Field.objects.filter(sheet=sheet1).count(), 3)
        self.assertEqual(Field.objects.filter(sheet=sheet1, active=True).count(), 2)
        self.assertEqual(Field.objects.filter(sheet=sheet2).count(), 2)  # inactive isn't copied


class IntegrationTestCase(TestCase):
    fixtures = ['basedata', 'coredata', 'onlineforms', 'onlineforms/extra_test_data']
    def setUp(self):
        self.client = Client()

    def test_valid_simple_initial_form_submission_loggedin(self):
        logged_in_person = Person.objects.get(userid="ggbaker")
        self.client.login_user(logged_in_person.userid)

        old_form_submission_count = len(FormSubmission.objects.all())
        old_sheet_submission_count = len(SheetSubmission.objects.all())

        url = reverse('onlineforms:sheet_submission_initial', kwargs={'form_slug': "comp-simple-form"})
        response = basic_page_tests(self, self.client, url)
        self.assertEqual(response.status_code, 200)
        # make sure it's not displaying the add-nonsfu form
        self.assertNotContains(response, '<input type="hidden" name="add-nonsfu" value="True"/>')
        # check for some important fields
        # note: the keys are the slugs of the field
        fill_data = {"favorite-color": "Black", "reason": "Because it's metal", "second-favorite-color": "Green"}
        # submit the form
        post_data = {
            '0': fill_data["favorite-color"],
            '1': fill_data["reason"],
            '2': fill_data["second-favorite-color"],
            'submit': "Yesplease",
        }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        # check that a success messaging is being displayed
        self.assertContains(response, '<li class="success">')
        # check that one form submission and one sheet submission got created
        self.assertEqual(old_form_submission_count + 1, len(FormSubmission.objects.all()))
        self.assertEqual(old_sheet_submission_count + 1, len(SheetSubmission.objects.all()))
        # find the submission in the database
        form_submission = FormSubmission.objects.latest('id')
        self.assertTrue(form_submission)
        sheet_submission = SheetSubmission.objects.latest('id')
        self.assertTrue(sheet_submission)
        self.assertEqual(sheet_submission.form_submission, form_submission)
        # make sure the person we logged in as got form initiator credits
        self.assertTrue(form_submission.initiator.isSFUPerson())
        self.assertEqual(form_submission.initiator.sfuFormFiller, logged_in_person)
        # do the same for the sheet submission
        self.assertTrue(sheet_submission.filler.isSFUPerson())
        self.assertEqual(sheet_submission.filler.sfuFormFiller, logged_in_person)
        # verify the data
        field_submissions = FieldSubmission.objects.filter(sheet_submission=sheet_submission).order_by('field__order')
        self.assertEqual(len(fill_data), len(field_submissions))
        for field_submission in field_submissions:
            self.assertEqual(fill_data[field_submission.field.slug], field_submission.data['info'])
        # check the sheet submission and form submission status
        self.assertEqual(sheet_submission.status, "DONE")
        # form submissions is pending until someone manually marks it done
        self.assertEqual(form_submission.status, "PEND")

    def test_valid_simple_initial_form_submission_anonymous(self):
        person = {'first_name': "Alan", 'last_name': "Turing", 'email_address': "alan.turing@example.net"}
        old_form_submission_count = len(FormSubmission.objects.all())
        old_sheet_submission_count = len(SheetSubmission.objects.all())

        url = reverse('onlineforms:sheet_submission_initial', kwargs={'form_slug': "comp-simple-form"})
        response = basic_page_tests(self, self.client, url)
        self.assertEqual(response.status_code, 200)
        # check that the non sfu form is up
        self.assertContains(response, '<input type="hidden" name="add-nonsfu" value="True"/>')
        # check for some important fields
        # note: the keys are the slugs of the field
        fill_data = {"favorite-color": "Black", "reason": "Because it's metal", "second-favorite-color": "Green"}
        # submit the form
        post_data = {
            'first_name': person["first_name"],
            'last_name': person["last_name"],
            'email_address': person["email_address"],
            'add-nonsfu': True,
            '0': fill_data["favorite-color"],
            '1': fill_data["reason"],
            '2': fill_data["second-favorite-color"],
            'submit': "Okay go",
        }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        # check that a success messaging is being displayed
        self.assertContains(response, '<li class="success">')
        # check that one form submission and one sheet submission got created
        self.assertEqual(old_form_submission_count + 1, len(FormSubmission.objects.all()))
        self.assertEqual(old_sheet_submission_count + 1, len(SheetSubmission.objects.all()))
        # find the submission in the database
        form_submission = FormSubmission.objects.latest('id')
        self.assertTrue(form_submission)
        sheet_submission = SheetSubmission.objects.latest('id')
        self.assertTrue(sheet_submission)
        self.assertEqual(sheet_submission.form_submission, form_submission)
        # make sure the person we logged in as got form initiator credits
        self.assertFalse(form_submission.initiator.isSFUPerson())
        self.assertEqual(form_submission.initiator.name(), "%s %s" % (person["first_name"], person["last_name"]))
        self.assertEqual(form_submission.initiator.email(), person["email_address"])
        # do the same for the sheet submission
        self.assertFalse(sheet_submission.filler.isSFUPerson())
        self.assertEqual(form_submission.initiator.name(), "%s %s" % (person["first_name"], person["last_name"]))
        self.assertEqual(form_submission.initiator.email(), person["email_address"])
        # verify the data
        field_submissions = FieldSubmission.objects.filter(sheet_submission=sheet_submission).order_by('field__order')
        self.assertEqual(len(fill_data), len(field_submissions))
        for field_submission in field_submissions:
            self.assertEqual(fill_data[field_submission.field.slug], field_submission.data['info'])
        # check the sheet submission and form submission status
        self.assertEqual(sheet_submission.status, "DONE")
        # form submissions is pending until someone manually marks it done
        self.assertEqual(form_submission.status, "PEND")

    def test_invalid_nonsfu_missing_elements(self):
        old_form_submission_count = len(FormSubmission.objects.all())
        old_sheet_submission_count = len(SheetSubmission.objects.all())

        url = reverse('onlineforms:sheet_submission_initial', kwargs={'form_slug': "comp-simple-form"})
        response = basic_page_tests(self, self.client, url)
        # test with each field missing
        person_nofirst = {'first_name': "", 'last_name': "Turing", 'email_address': "alan.turing@example.net"}
        person_nolast = {'first_name': "Alan", 'last_name': "", 'email_address': "alan.turing@example.net"}
        person_noemail = {'first_name': "Alan", 'last_name': "Turing", 'email_address': ""}
        people = [person_nofirst, person_nolast, person_noemail]
        fill_data = {"favorite-color": "Black", "reason": "Because it's metal", "second-favorite-color": "Green"}

        for person in people:
            # submit with empty user info
            post_data = {
                'first_name': person['first_name'],
                'last_name': person['last_name'],
                'email_address': person['email_address'],
                'add-nonsfu': True,
                '0': fill_data["favorite-color"],
                '1': fill_data["reason"],
                '2': fill_data["second-favorite-color"],
                'submit': "Yes",
            }

            response = self.client.post(url, post_data, follow=True)
            self.assertEqual(response.status_code, 200)
            # make sure no success
            self.assertNotContains(response, '<li class="success">')
            # make sure there was an error
            self.assertContains(response, '<li class="error">')
            # make sure nothing got added to the database
            self.assertEqual(old_form_submission_count, len(FormSubmission.objects.all()))
            self.assertEqual(old_sheet_submission_count, len(SheetSubmission.objects.all()))

    def test_invalid_forbidden_initial(self):
        # this form doesn't allow non-sfu students to fill it out, so if we
        # are not logged in and we try to access it it should return forbidden
        url = reverse('onlineforms:sheet_submission_initial', kwargs={'form_slug': "comp-multi-sheet-form"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    
    #def test_create_fields(self):
    #    for key, model in FIELD_TYPE_MODELS:
    #        print model


class ViewTestCase(TestCase):
    fixtures = ['basedata', 'coredata', 'onlineforms', 'onlineforms/extra_test_data']
    slug_data = {'formgroup_slug': "cmpt-admins",
                'formsubmit_slug': "submission-comp-simple-form-2",
                'form_slug': "comp-simple-form",
                'sheet_slug': "initial",
                'field_slug': "favorite-color",
                'sheetsubmit_slug': "submission-initial-2",
                'secret_url': "b50d3a695edf877df2a2100376d493f1aec5c26a",
                'non_initial_sheet_slug': "initial-000",
                'non_initial_sheetsubmit_slug': "submission-noninitial"}

    def setUp(self):
        self.client = Client()
        logged_in_person = Person.objects.get(userid="dzhao")
        self.client.login_user(logged_in_person.userid)
        # make sure the sheetsub is owned by the logged in user (to correct for wonky test data)
        sheetsub = SheetSubmission.objects.get(form_submission__slug=self.slug_data["formsubmit_slug"], slug=self.slug_data["sheetsubmit_slug"])
        ff = sheetsub.filler
        ff.sfuFormFiller = logged_in_person
        ff.save()

    def test_no_arg_pages(self):
        views = ['manage_groups',
                        'new_group',
                        'admin_list_all',
                        'admin_assign_any',
                        'list_all',
                        'new_form',
                        'index']
        self.run_basic_page_tests(views, {})

    def test_formgroup_pages(self):
        views = ['manage_group']
        args = {'formgroup_slug': self.slug_data["formgroup_slug"]}
        self.run_basic_page_tests(views, args)

    def test_form_pages(self):
        views = ['view_form', 'edit_form', 'preview_form', 'new_sheet', 'sheet_submission_initial']
        args = {'form_slug': self.slug_data["form_slug"]}
        self.run_basic_page_tests(views, args)

    def test_sheet_pages(self):
        views = ['edit_sheet', 'edit_sheet_info', 'new_field']
        args = {'form_slug': self.slug_data["form_slug"], 'sheet_slug': self.slug_data["sheet_slug"]}
        self.run_basic_page_tests(views, args)

    def test_field_pages(self):
        views = ['edit_field']
        args = {'form_slug': self.slug_data["form_slug"],
                'sheet_slug': self.slug_data["sheet_slug"],
                'field_slug': self.slug_data["field_slug"]}
        self.run_basic_page_tests(views, args)

    def test_form_submission_pages(self):
        views = ['view_submission']
        args = {'form_slug': self.slug_data["form_slug"], 'formsubmit_slug': self.slug_data["formsubmit_slug"]}
        self.run_basic_page_tests(views, args)

    def test_secret_url_pages(self):
        views = ['sheet_submission_via_url']
        args = {'secret_url': self.slug_data["secret_url"]}
        self.run_basic_page_tests(views, args)

    def test_total_submission_pages(self):
        views = ['sheet_submission_subsequent']
        args = {'form_slug': self.slug_data["form_slug"],
                'sheet_slug': self.slug_data["non_initial_sheet_slug"],
                'formsubmit_slug': self.slug_data["formsubmit_slug"],
                'sheetsubmit_slug': self.slug_data["non_initial_sheetsubmit_slug"]}
        self.run_basic_page_tests(views, args)

        views = ['admin_return_sheet']
        del args['sheet_slug']
        self.run_basic_page_tests(views, args)

    def test_admin_submission(self):
        views = ['view_submission',]
        args = {'form_slug': self.slug_data["form_slug"], 'formsubmit_slug': self.slug_data["formsubmit_slug"]}
        self.run_basic_page_tests(views, args)
        sheetsub = SheetSubmission.objects.get(form_submission__slug=self.slug_data["formsubmit_slug"], slug=self.slug_data["sheetsubmit_slug"])
        sheetsub.status = 'DONE'
        sheetsub.save()
        self.run_basic_page_tests(views, args)

    def run_basic_page_tests(self, views, arguments):
        for view in views:
            try:
                url = reverse('onlineforms:' + view, kwargs=arguments)
                response = basic_page_tests(self, self.client, url)
                self.assertEqual(response.status_code, 200)
            except:
                print("with view==" + repr(view))
                raise

    def test_returning_initial_sheet(self):
        # We should no longer be able to return the initial sheet.
        args = {'form_slug': self.slug_data["form_slug"],
                'formsubmit_slug': self.slug_data["formsubmit_slug"],
                'sheetsubmit_slug': self.slug_data["sheetsubmit_slug"]}
        try:
            url = reverse('onlineforms:admin_return_sheet', kwargs=args)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
        except:
            print("with view == views.admin_return_sheet")
            raise


class MiscTests(TestCase):
    fixtures = ['basedata', 'coredata', 'onlineforms', 'onlineforms/extra_test_data']

    def test_sheet_submission_get_url(self):
        # arrange
        slugs = {'sheetsubmit_slug': "submission-initial-2",
                'sheet_slug': "initial",
                'formsubmit_slug': "submission-comp-simple-form-2",
                'form_slug': "comp-simple-form"
        }
        form = Form.objects.get(slug=slugs['form_slug'])
        form_submission = FormSubmission.objects.get(form=form, slug=slugs['formsubmit_slug'])
        sheet = Sheet.objects.get(form=form, slug=slugs['sheet_slug'])
        sheet_submission = SheetSubmission.objects.get(sheet=sheet, form_submission=form_submission, slug=slugs['sheetsubmit_slug'])
        # act
        url = sheet_submission.get_submission_url()
        # assert, check that we get a full URL with all the slugs
        expected_url = reverse('onlineforms:sheet_submission_subsequent', kwargs=slugs)
        self.assertEqual(url, expected_url)

    def test_sheet_submission_get_url_secret(self):
        # arrange
        key = "b50d3a695edf877df2a2100376d493f1aec5c26a"
        sheet_submission = SheetSubmissionSecretUrl.objects.get(key=key).sheet_submission
        # act
        url = sheet_submission.get_submission_url()
        # assert, check that we get a URL using the key, not all the slugs
        expected_url = reverse('onlineforms:sheet_submission_via_url', kwargs={'secret_url': key})
        self.assertEqual(url, expected_url)


class FieldTestCase(TestCase):
    fixtures = ['basedata', 'coredata', 'onlineforms', 'onlineforms/extra_test_data']
    # one config file the should handle most fields
    standard_config = {"min_length": 1,
                        "max_length": 10,
                        "required": False,
                        "help_text": "whatever",
                        "label": "whatever",
                        "min_responses": 1,
                        "max_responses": 4}

    def setUp(self):
        self.client = Client()
        self.unit = Unit.objects.get(label="CMPT")
        # we want to be logge din for all these tests
        logged_in_person = Person.objects.get(userid="ggbaker")
        self.client.login_user(logged_in_person.userid)

    def test_make_config_form(self):
        for (name, field_model) in FIELD_TYPE_MODELS.items():
            instance = field_model(self.standard_config)
            config_form = instance.make_config_form()
            # looks like a divider will return a bool false here, look into that
            # still checks for notimplemented error though
            if config_form:
                self.assertTrue(isinstance(config_form, DjangoForm))

    def test_make_entry_field(self):
        for (name, field_model) in FIELD_TYPE_MODELS.items():
            instance = field_model(self.standard_config)
            self.assertTrue(isinstance(instance.make_entry_field(), DjangoFormsField))

    def test_serialize_field(self):
        for (name, field_model) in FIELD_TYPE_MODELS.items():
            instance = field_model(self.standard_config)
            self.assertTrue(isinstance(instance.serialize_field("test data"), dict))

    def test_smltxt_field(self):
        test_input = "abacus"
        config = self.standard_config.copy()
        field_submission = self.field_test("SMTX", config, test_input)
        self.assertEqual(field_submission.data["info"], test_input)

    def test_medtxt_field(self):
        test_input = repeat_to_length("Never Eat Shredded Wheat.", 351)
        config = self.standard_config.copy()
        config["min_length"] = 320
        config["max_length"] = 377
        field_submission = self.field_test("MDTX", config, test_input)
        self.assertEqual(field_submission.data["info"], test_input)

    def test_lrgtxt_field(self):
        test_input = repeat_to_length("The quick brown fox jumps over the lazy dog.", 443)
        config = self.standard_config.copy()
        config["min_length"] = 401
        config["max_length"] = 490
        field_submission = self.field_test("LGTX", config, test_input)
        self.assertEqual(field_submission.data["info"], test_input)

    def test_email_field(self):
        test_input = "person@example.com"
        config = self.standard_config.copy()
        field_submission = self.field_test("EMAI", config, test_input)
        self.assertEqual(field_submission.data["info"], test_input)

    def test_radio_field(self):
        # config data for the radio button
        test_data = [{"key": "choice_1", "value": "AM"},
                        {"key": "choice_2", "value": "FM"},
                        {"key": "choice_3", "value": "TAPE"}]
        # which value from above we are going to select
        test_input = test_data[1]
        config = self.standard_config.copy()
        for test in test_data:
            config[test["key"]] = test["value"]
        field_submission = self.field_test("RADI", config, test_input["key"])
        # the key is stored in the field submission, not the actual value
        self.assertEqual(field_submission.data["info"], test_input["key"])
        # check the value by going through the field config
        self.assertEqual(field_submission.field.config[field_submission.data["info"]], test_input["value"])

    def test_dropdown_field(self):
        # config data for the radio button
        test_data = [{"key": "choice_1", "value": "Yes"},
                        {"key": "choice_2", "value": "No"},
                        {"key": "choice_3", "value": "Maybe"}]
        # which value from above we are going to select
        test_input = test_data[2]
        config = self.standard_config.copy()
        for test in test_data:
            config[test["key"]] = test["value"]
        field_submission = self.field_test("SEL1", config, test_input["key"])
        # the key is stored in the field submission, not the actual value
        self.assertEqual(field_submission.data["info"], test_input["key"])
        # check the value by going through the field config
        self.assertEqual(field_submission.field.config[field_submission.data["info"]], test_input["value"])

    def test_multiselect_field(self):
        # config data for the radio button
        test_data = [{"key": "choice_1", "value": "Apple"},
                        {"key": "choice_2", "value": "Orange"},
                        {"key": "choice_3", "value": "Pear"},
                        {"key": "choice_4", "value": "Banana"}]
        # which value from above we are going to select
        test_selected = [test_data[1], test_data[3]]
        test_not_selected = [test_data[0], test_data[2]]
        config = self.standard_config.copy()
        for test in test_data:
            config[test["key"]] = test["value"]
        field_submission = self.field_test("SELN", config, [select["key"] for select in test_selected])
        # construct a list of the actual values we could get from the db
        in_db_values = [field_submission.field.config[key] for key in field_submission.data["info"]]
        # check the values we selected are in the field submission
        for selected in test_selected:
            # the key is stored in the field submission, not the actual value
            self.assertIn(selected["key"], field_submission.data["info"])
            # check the value by going through the field config
            self.assertIn(selected["value"], in_db_values)
        # check the values we did not select are not in the field submission
        for not_selected in test_not_selected:
            # the key is stored in the field submission, not the actual value
            self.assertNotIn(not_selected["key"], field_submission.data["info"])
            # check the value by going through the field config
            self.assertNotIn(not_selected["value"], in_db_values)

    # takes a fieldtype, field config, and input.
    # will create a form with one sheet with one field of
    # the type specified with the config specified. Will then
    # submit the sheet with test_input, and will return the field submission
    def field_test(self, fieldtype, config, test_input):
        # create a basic form with one field to submit
        fg = FormGroup.objects.create(name="Admin Test", unit=self.unit)
        form = Form.objects.create(title="Test Form", unit=self.unit, owner=fg, initiators="LOG")
        sheet = Sheet.objects.create(title="Initial Sheet", form=form, is_initial=True)
        field = Field.objects.create(label="F1", sheet=sheet, fieldtype=fieldtype, config=config)
        # make a post request to submit the sheet
        post_data = {'0': test_input, 'submit': "submit"}
        url = reverse('onlineforms:sheet_submission_initial', kwargs={'form_slug': form.slug})
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        # ensure objects were created
        self.assertEqual(len(FormSubmission.objects.filter(form=form)), 1)
        self.assertEqual(len(SheetSubmission.objects.filter(sheet=sheet)), 1)
        field_submissions = FieldSubmission.objects.filter(field=field)
        self.assertEqual(len(field_submissions), 1)
        return field_submissions[0]
