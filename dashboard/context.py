from django.conf import settings

def media(request):
    """
    Add context things that we need
    """
    # GRAD_DATE(TIME?)_FORMAT for the grad/ra/ta apps
    return {'GRAD_DATE_FORMAT': settings.GRAD_DATE_FORMAT,
            'GRAD_DATETIME_FORMAT': settings.GRAD_DATETIME_FORMAT,
            'LOGOUT_URL': settings.LOGOUT_URL,
            'LOGIN_URL': settings.LOGIN_URL,}