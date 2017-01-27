import random


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
        value = "script-src 'self' 'nonce-%s'" % (token,)

        if header in response:
            return response

        #response[header] = value
        return response


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