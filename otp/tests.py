from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from courselib.testing import Client, test_views

from django.contrib.auth.models import User
from django.utils import timezone
import datetime

from django_otp.plugins.otp_totp.models import TOTPDevice
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
        session_info = SessionInfo.for_sessionstore(c.session)

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
        session_info.last_2fa = timezone.now()
        session_info.save()
        # (mock django_otp's login())
        from django_otp import DEVICE_ID_SESSION_KEY
        session = c.session
        session._session[DEVICE_ID_SESSION_KEY] = device.persistent_id
        session.save()

        resp = c.get(url)
        self.assertEqual(resp.status_code, 200)

        # now fiddle with the ages of things and check for the right failures

        # old password login: should redirect -> login -> password login
        session_info.last_auth = timezone.now() - datetime.timedelta(days=2)
        session_info.save()
        resp = c.get(url, follow=True)
        self.assertEqual(len(resp.redirect_chain), 2)
        self.assertTrue(resp.redirect_chain[-1][0].startswith(str(settings.PASSWORD_LOGIN_URL) + '?'))

        # old 2fa: should redirect -> 2fa login
        session_info.last_auth = timezone.now() - datetime.timedelta(hours=1)
        session_info.last_2fa = timezone.now() - datetime.timedelta(days=30)
        session_info.save()

        resp = c.get(url, follow=True)
        self.assertEqual(len(resp.redirect_chain), 1)
        self.assertTrue(resp.redirect_chain[-1][0].startswith(str(settings.LOGIN_URL) + '?'))