from django.core.management.base import BaseCommand
import os, stat, subprocess

import courses.secrets as secrets
from dashboard.photos import get_photo_password, set_photo_password

class Command(BaseCommand):
    def _report_missing(self, config, obj):
        print("Warning: Not installing %s since %s not set in secrets.py." % (obj, config))

    def _install_from(self, config, filename, mode=stat.S_IRUSR):
        if hasattr(secrets, config) and getattr(secrets, config):
            content = getattr(secrets, config)
            fh = open(filename, 'w')
            fh.write(content)
            fh.close()
            os.chmod(filename, mode)
            # TODO: maybe need to os.chown(filename, uid, gid) as well?

        else:
            self._report_missing(config, filename)


    def handle(self, *args, **kwargs):

        # AMPQ user
        if hasattr(secrets, 'AMPQ_PASSWORD') and getattr(secrets, 'AMPQ_PASSWORD'):
            user = 'coursys'
            vhost = 'myvhost'
            pw = getattr(secrets, 'AMPQ_PASSWORD')

            subprocess.call(['rabbitmqctl', '-q', 'add_user', user, pw])
            subprocess.call(['rabbitmqctl', '-q', 'add_vhost', vhost])
            subprocess.call(['rabbitmqctl', '-q', 'set_permissions', '-p', vhost, user, '.*', '.*', '.*'])
            subprocess.call(['rabbitmqctl', '-q', 'change_password', user, pw]) # to change if necessary: add_user doesn't
            subprocess.call(['rabbitmqctl', '-q', 'change_password', 'guest', pw]) # hey, there's a guest account

        else:
            self._report_missing('AMPQ_PASSWORD', 'AMPQ user')

        # photo system initial password
        try:
            get_photo_password()
            photo_pass_needed = False
        except KeyError:
            photo_pass_needed = True

        if photo_pass_needed:
            if hasattr(secrets, 'INITIAL_PHOTO_PASSWORD') and getattr(secrets, 'INITIAL_PHOTO_PASSWORD'):
                pw = getattr(secrets, 'INITIAL_PHOTO_PASSWORD')
                set_photo_password(pw)
            else:
                self._report_missing('INITIAL_PHOTO_PASSWORD', 'photo password')

