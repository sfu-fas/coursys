from django.apps import AppConfig

class CoredataConfig(AppConfig):
    name = 'coredata'


from django.core.checks import Error, register


@register()
def sanity_check(app_configs, **kwargs):
    errors = []

    # if 'IN_DOCKER' in os.environ :
    from coredata import panel
    _, failed = panel.sanity_checks()
    errors.extend([Error(f'Failed sanity check: {check}', hint=descr) for check, descr in failed])

    return errors
