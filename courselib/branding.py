# What is this product called? Only this code can tell.

# The 'hint' argument can be used to give a hint about what kind of access is happening, if no 'request' is available.
# Allowed values: 'course', 'admin'


def help_email(request=None, hint='course'):
    return 'coursys-help@sfu.ca'


def product_name(request=None, hint='course'):
    return 'CourSys'
