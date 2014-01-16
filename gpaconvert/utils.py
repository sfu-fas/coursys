import functools

from django.db import models
from django.shortcuts import render_to_response
from django.template import RequestContext


# XXX: Consider using django-annoying's render_to instead.
def render_to(template_filepath):
    """
    Shortcut for automatically rendering and returning your template if your view returns
    a dictionary.

    Example:
        @render_to('path/to/template.html')
        def my_view(request):
            return {
                'foo': 'bar',
            }

        template.html will be rendered using the returned dictionary as context.
    """
    def wrapper(func):
        @functools.wraps(func)
        def func_wrapper(request, *args, **kwargs):
            result = func(request, *args, **kwargs)
            if isinstance(result, dict):
                return render_to_response(template_filepath, result,
                                          context_instance=RequestContext(request))
            else:
                return result
        return func_wrapper
    return wrapper


# XXX: This is also provided in django-annoying.
def get_object_or_None(model_thing, **kwargs):
    """
    Shortcut to catch the exception thrown by Model.objects.get if nothing is found and
    returns None instead.

    Example:
        obj = get_object_or_None(MyModelClass, id=3)
    """
    if isinstance(model_thing, models.Manager):
        try:
            return model_thing.get(**kwargs)
        except model_thing.model.DoesNotExist:
            return None
    else:
        try:
            return model_thing.objects.get(**kwargs)
        except model_thing.DoesNotExist:
            return None
