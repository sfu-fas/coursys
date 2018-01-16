import random
from django.views.decorators.csrf import csrf_exempt

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

        #header = 'Content-Security-Policy'
        header = 'Content-Security-Policy-Report-Only'
        #value = "default-src 'self' * ; script-src 'self' * 'nonce-%s' 'unsafe-inline'" % (token,)
        value = "default-src 'self' * ; " \
                "style-src 'self' 'unsafe-inline' ; " \
                "img-src 'self' www.sfu.ca data: ; " \
                "font-src 'self' www.sfu.ca ; " \
                "script-src 'self' 'nonce-%s' ; " \
                "report-uri /csp-reports ; " \
                % (token,)

        if header in response:
            return response

        #response[header] = value
        return response


@csrf_exempt
def csp_report_view(request):
    from django.http.response import HttpResponse
    import json
    report = json.loads(request.body.decode('utf8'))
    print(json.dumps(report, indent=2))
    return HttpResponse()


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