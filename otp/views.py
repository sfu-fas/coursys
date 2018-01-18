from django.shortcuts import render
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django_cas.views import _redirect_url

from courselib.auth import ForbiddenResponse, NotFoundResponse
from courselib.branding import help_email
from six import BytesIO
from six.moves.urllib.parse import urlencode
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp import login as otp_login

from .models import SessionInfo, all_otp_devices, totpauth_url, needs_2fa
from .forms import TokenForm

import base64
import datetime
import qrcode
import qrcode.image.svg

from log.models import LogEntry # CourSys-specific
from ipware import ip


def _setup_view(request, next_page):
    '''
    Common logic to set up these views: make sure Django auth is done and check our conditions.
    '''
    if not next_page and 'next' in request.GET:
        next_page = request.GET['next']
    if not next_page:
        next_page = _redirect_url(request)

    if not request.maybe_stale_user.is_authenticated:
        # Not authenticated at all. Force standard-Django auth.
        return next_page, False, False

    good_auth, good_2fa = request.session_info.okay_auth(request, request.maybe_stale_user)

    return next_page, good_auth, good_2fa


def login_2fa(request, next_page=None):
    next_page, okay_auth, okay_2fa = _setup_view(request, next_page)

    if not okay_auth:
        # Stale standard-Django authentication: redirect to password login page.
        return HttpResponseRedirect(settings.PASSWORD_LOGIN_URL + '?' + urlencode({'next': next_page}))

    if not okay_2fa:
        # Need to do 2FA for this user.
        devices = list(all_otp_devices(request.maybe_stale_user))
        if not devices:
            messages.add_message(request, messages.WARNING, 'You are required to do two-factor authentication but have no device enabled. You must add one.')
            return HttpResponseRedirect(reverse('otp:add_topt') + '?' + urlencode({'next': next_page}))

        if request.method == 'POST':
            form = TokenForm(data=request.POST, devices=devices)
            if form.is_valid():
                # OTP is valid: record last 2FA time in SessionInfo; have django_otp record what it needs in the session
                SessionInfo.just_2fa(request)
                request.user = request.maybe_stale_user # otp_login looks at request.user
                otp_login(request, form.device)

                l = LogEntry(userid=request.user.username,
                    description=("2FA as %s from %s") % (request.user.username, ip.get_ip(request)),
                    related_object=request.user)
                l.save()

                return HttpResponseRedirect(next_page)
        else:
            form = TokenForm()

        context = {
            'form': form,
        }
        return render(request, 'otp/login_2fa.html', context)

    return HttpResponseRedirect(next_page)


def add_topt(request, next_page=None):
    next_page, okay_auth, okay_2fa = _setup_view(request, next_page)

    if not okay_auth:
        return ForbiddenResponse(request)

    # This enforces that users have exactly one TOTP. That *seems* like the best practice.
    devices = TOTPDevice.objects.devices_for_user(request.maybe_stale_user, confirmed=True)
    if devices:
        return ForbiddenResponse(request, "You have already configured an authenticator with this account, and cannot add another. Contact %s if you are unable to authenticate with CourSys", (help_email(request),))

    device = TOTPDevice(user=request.maybe_stale_user, name='Authenticator, enabled %s' % (datetime.date.today()))
    device.save()

    l = LogEntry(userid=request.user.username,
                 description=("Added TOPT from %s") % (ip.get_ip(request),),
                 related_object=device)
    l.save()

    # build QR code
    uri = totpauth_url(device)
    qr = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage)
    qrdata = BytesIO()
    qr.save(qrdata)
    # This is the OTP secret (bits) encoded as base32, wrapped in an otpauth URL, encoded as a QR code, encoded as an
    # SVG, encoded as base64, wrapped in a data URL. I'm strangely proud.
    dataurl = b'data:image/svg+xml;base64,' + base64.b64encode(qrdata.getvalue())

    context = {
        'device': device,
        'dataurl': dataurl,
        'next_page': next_page,
    }
    return render(request, 'otp/add_topt.html', context)