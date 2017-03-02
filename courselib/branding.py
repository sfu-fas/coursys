# What is this product called? Only this code can tell.

# The 'hint' argument can be used to give a hint about what kind of access is happening, if no 'request' is available.
# Allowed values: 'course', 'admin', 'forms'


def help_email(request=None, hint='course'):
    return 'coursys-help@sfu.ca'


def product_name(request=None, hint='course'):
    if request:
        hostname = str(request.get_host()).lower()
        if hostname.startswith('fasit'):
            return 'FASit'
        elif hostname.startswith('courses') or hostname.startswith('coursys'):
            return 'CourSys'
        elif hostname.startswith('localhost'):
            return 'CourSys/FASit - DEV'

    if hint and hint == 'admin':
        return 'FASit'

    return 'CourSys'
