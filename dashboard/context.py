from pathlib import Path
import socket

from django.conf import settings
from django.utils.safestring import mark_safe
from coredata.models import Member
from cache_utils.decorators import cached
from courselib.branding import product_name, help_email


@cached(3600)
def is_instr_ta(userid):
    if not userid:
        return False
    members = Member.objects.filter(role__in=['INST', 'TA'])
    return members.exists()


def get_server_message(config: str, filename: Path) -> str:
    """
    Find a server-wide message, if provided anywhere by admins.

    If set (and non-empty) in settings.THE_CONFIG then use that.
    If the file is present, read that and use it.
    """
    if hasattr(settings, config):
        # if the message is set in settings.py, honour it.
        cfg_msg = getattr(settings, config)
        if len(cfg_msg) > 0:
            return cfg_msg

    try:
        file_msg = open(filename, 'rt', encoding='utf-8').read()
        return mark_safe(file_msg)
    except FileNotFoundError as e:
        return ''
    except Exception as e:
        # file unreadable: output something for gunicorn logs
        print(f'Could not read server message {filename}: {e}')
        return ''


def media(request):
    """
    Add context things that we need
    """
    # A/B testing: half of instructors and TAs see a different search box
    instr_ta = is_instr_ta(request.user.username)
    instr_ta_ab = instr_ta and request.user.is_authenticated and request.user.id % 2 == 0
    # GRAD_DATE(TIME?)_FORMAT for the grad/ra/ta apps
    return {'GRAD_DATE_FORMAT': settings.GRAD_DATE_FORMAT,
            'GRAD_DATETIME_FORMAT': settings.GRAD_DATETIME_FORMAT,
            'LOGOUT_URL': settings.LOGOUT_URL,
            'LOGIN_URL': settings.LOGIN_URL,
            'STATIC_URL': settings.STATIC_URL,
            'is_instr_ta': instr_ta,
            'instr_ta_ab': instr_ta_ab,
            'request_path': request.path,
            'CourSys': product_name(request),
            'help_email': help_email(request),
            'SERVER_MESSAGE_INDEX': get_server_message('SERVER_MESSAGE_INDEX', Path('/dynamic_config/server_message_index.html')),
            'SERVER_MESSAGE': get_server_message('SERVER_MESSAGE', Path('/dynamic_config/server_message.html')),
            'SERVER_HOSTNAME': socket.gethostname(),
            }
