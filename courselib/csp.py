import json
import random
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http.response import HttpResponse
from log.models import LogEntry
from coredata.models import Unit

generic_related = Unit.objects.get(slug='univ')


def new_token():
    """
    Randomly-generated token
    """
    # from http://stackoverflow.com/a/2782859/6871666
    return '%010x' % random.randrange(16**10)


class CSPMiddleware(object):
    """
    Middleware to add a Content-Security-Policy header and generate a nonce for each response.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = new_token()
        request.csp_nonce = token
        response = self.get_response(request)

        if settings.DEBUG:
            header = 'Content-Security-Policy'
        else:
            header = 'Content-Security-Policy-Report-Only'
            return response # short-circuit for now

        if header in response:
            # if the view set the Content-Security-Policy, honour it
            return response

        extra_script_src = " 'nonce-%s'" % (token,)
        extra_style_src = ''
        if hasattr(response, 'allow_gstatic_csp') and response.allow_gstatic_csp:
            # pages that use Google charts need to load/run that code...
            extra_script_src += " https://www.gstatic.com https://www.google.com 'unsafe-eval'"
            extra_style_src = ' https://www.gstatic.com https://ajax.googleapis.com https://www.google.com'

        if hasattr(response, 'has_inline_script') and response.has_inline_script:
            # """'unsafe-inline' is ignored if either a hash or nonce value is present in the source list"""
            extra_script_src = " 'unsafe-inline' 'unsafe-eval'"

        value = "default-src 'self' * ; " \
                "style-src 'self' 'unsafe-inline'%s ; " \
                "img-src 'self' www.sfu.ca data: ; " \
                "font-src 'self' www.sfu.ca ; " \
                "script-src 'self' %s ; " % (extra_style_src, extra_script_src)
        value += "report-uri /csp-reports ;"

        response[header] = value
        return response


@csrf_exempt
def csp_report_view(request):
    report_json = request.body.decode('utf8')
    report = json.loads(report_json)
    resp = HttpResponse()

    if 'script-sample' in report['csp-report'] and 'var t=0,e=function(t,e){ret' in report['csp-report']['script-sample']:
        # firefox browser plugin injection?
        return resp

    userid = request.user.username if request.user.is_authenticated else '_anon'
    l = LogEntry(userid=userid, description='CSP violation', comment=report_json, related_object=generic_related)
    l.save()

    if settings.DEBUG:
        print(json.dumps(report, indent=2))

    return resp


def context_processor(request):
    """
    Inject the CSP nonce into the context, allowing this in templates where we shouldn't have inline JS, but do anyway:
    <script nonce="{{ CSP_NONCE }}">
    """
    if hasattr(request, 'csp_nonce'):
        return {'CSP_NONCE': request.csp_nonce}
    else:
        # some middleware has short-circuited CSPMiddleware: make sure there is some token there
        return {'CSP_NONCE': new_token()}