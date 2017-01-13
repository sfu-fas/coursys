from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponseRedirect
from django_cas.views import _redirect_url

from six.moves.urllib.parse import urlencode
from django_otp.forms import OTPTokenForm

def login_2fa(request, next_page=None):
    if not next_page and 'next' in request.GET:
        next_page = request.GET['next']
    if not next_page:
        next_page = _redirect_url(request)

    if not request.user.is_authenticated():
        # need them to be CAS-authenticated first: redirect to normal login page
        return HttpResponseRedirect(settings.LOGIN_URL + '?' + urlencode({'next': next_page}))

    print OTPTokenForm(user=request.user, request=request)

    if request.user.is_verified():
        return HttpResponseRedirect(next_page)
