from django.test import TestCase
from django.core.urlresolvers import reverse
from django.conf import settings
from courselib.testing import TEST_COURSE_SLUG, Client, test_views

from django.contrib.auth.models import User
from django.utils import timezone

from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp import login as otp_login
from .models import SessionInfo
from coredata.models import Person

class OTPTest(TestCase):
    fixtures = ['basedata', 'coredata']

    def test_otp_auth(self):
        c = Client()
        person = Person.objects.get(userid='ggbaker')
        url = reverse('dashboard:index')

        # no auth: should redirect to 2fa login, and then to password login
        resp = c.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp['location'].startswith(str(settings.LOGIN_URL) + '?'))

        nexturl = resp['location']
        resp = c.get(nexturl)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp['location'].startswith(str(settings.PASSWORD_LOGIN_URL) + '?'))

        # do the standard Django auth: should be okay for now, since user doesn't need 2FA.
        c.login_user('ggbaker')
        user = User.objects.get(username='ggbaker')
        c._login(user)
        # mock the SessionInfo into place for the tests
        si = SessionInfo.for_session_key(c.session.session_key)
        si.last_auth = timezone.now()
        si.save()

        resp = c.get(url)
        self.assertEqual(resp.status_code, 200)

        # set the user's account to need 2FA: now should be redirected to create a TOPT.
        person.config['2fa'] = True
        person.save()

        resp = c.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp['location'].startswith(str(settings.LOGIN_URL) + '?'))

        nexturl = resp['location']
        resp = c.get(nexturl)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp['location'].startswith(reverse('otp:add_topt')))

        test_views(self, c, 'otp:', ['add_topt'], {})

        # create a fake TOTP device for the user
        TOTPDevice.objects.filter(user=user).delete()
        key = '0'*20
        device = TOTPDevice(user=user, name='test device', confirmed=True, key=key)
        device.save()

        # ... now we should see the 2FA screen
        resp = c.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp['location'].startswith(str(settings.LOGIN_URL) + '?'))

        nexturl = resp['location']
        resp = c.get(nexturl)
        self.assertEqual(resp.status_code, 200)

        test_views(self, c, 'otp:', ['login_2fa'], {})

        # if we fake the 2FA login, we should be seeing pages again
        si.last_2fa = timezone.now()
        si.save()
        c.user = user  # otp_login looks at request.user
        otp_login(c, device)

        resp = c.get(url)
        self.assertEqual(resp.status_code, 200)
