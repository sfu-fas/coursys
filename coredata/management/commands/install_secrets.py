from django.core.management.base import BaseCommand
import os, stat, subprocess

import courses.secrets as secrets

class Command(BaseCommand):
    def _report_missing(self, config, obj):
        print "Warning: Not installing %s since %s not set in secrets.py." % (obj, config)

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
        #self._install_from('STUNNEL_PEM', '/etc/stunnel/stunnel.pem')
        #self._install_from('CERT_PEM', '/etc/nginx/cert.pem')
        #self._install_from('CERT_KEY', '/etc/nginx/cert.key')

        # AMPQ user
        if hasattr(secrets, 'AMPQ_PASSWORD') and getattr(secrets, 'AMPQ_PASSWORD'):
            user = 'coursys'
            vhost = 'myvhost'
            pw = getattr(secrets, 'AMPQ_PASSWORD')

            subprocess.call(['rabbitmqctl', '-q', 'add_user', user, pw])
            subprocess.call(['rabbitmqctl', '-q', 'add_vhost', vhost])
            subprocess.call(['rabbitmqctl', '-q', 'set_permissions', '-p', vhost, user, '.*', '.*', '.*'])

        else:
            self._report_missing('AMPQ_PASSWORD', 'AMPQ user')



