"""
Code for managing CSRPT authentication.
"""

import os
import shutil
import subprocess
import time
from typing import Optional

from django.conf import settings


username_file = os.path.join(settings.CSRPT_AUTH_FILES, 'username')
keytab_file = os.path.join(settings.CSRPT_AUTH_FILES, 'adsfu.keytab')
ticket_file = os.path.join(settings.CSRPT_AUTH_FILES, 'krb5cc')


def get_output(process: subprocess.Popen):
    buffer = ""
    while True:
        data = process.stdout.read(1)
        if data != "":
            buffer += data
        else:
            break
    return buffer


def initial_csrpt_auth(username: str, password: str, get_cert: bool = True) -> Optional[str]:
    """
    Authenticate a user against the CSRPT service, creating keytab.
    Returns None or an error message.
    """
    assert '\n' not in password and '\r' not in password, "cannot safely have ktutil conversation"

    ktutil = subprocess.Popen(['/usr/bin/ktutil'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='ascii')
    
    ktutil.stdin.write(f"addent -password -p {username}@AD.SFU.CA -k 1 -e aes256-cts-hmac-sha1-96\n")
    time.sleep(0.5)  # give ktutil a moment to expect the password
    ktutil.stdin.write(f"{password}\n")
    ktutil.stdin.write(f"addent -password -p {username}@AD.SFU.CA -k 1 -e aes128-cts-hmac-sha1-96\n")
    time.sleep(0.5)  # give ktutil a moment to expect the password
    ktutil.stdin.write(f"{password}\n")
    ktutil.stdin.write(f"wkt {keytab_file}\n")
    try:
        stdout, stderr = ktutil.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        ktutil.kill()
        return "ktutil process timed out"

    if ktutil.returncode != 0:
        return stdout + stderr

    with open(username_file, 'wt', encoding='ascii') as f:
        f.write(username)
    
    if get_cert:
        return refresh_csrpt_auth()
    else:
        return None
    

def refresh_csrpt_auth() -> Optional[str]:
    """
    Refresh the CSRPT authentication by renewing the keytab file to get a ticket.
    Returns None or an error message.
    """
    username = open(username_file, 'rt', encoding='ascii').read().strip()

    kinit = subprocess.Popen(['/usr/bin/kinit', f'{username}@AD.SFU.CA', '-k', '-t', keytab_file])
    try:
        kinit.wait(timeout=10)
    except subprocess.TimeoutExpired:
        kinit.kill()
        return "kinit process timed out"

    if kinit.returncode != 0:
        return f'kinit exited {kinit.returncode}'

    # Juggle the ticket into the shared location so other workers can see it.
    temp_ticket = f'/tmp/krb5cc_{os.getuid()}'

    if not os.path.isfile(temp_ticket) or os.path.islink(temp_ticket):
        return f'ticket in {temp_ticket} is not a regular file, which is what we assume'

    shutil.move(temp_ticket, ticket_file)

    # Us and other containers will have this same symlink. (Others have it from the docker recipe.)
    # ... so the ticket can be shared by any container with /csrpt_auth mounted.
    os.symlink(ticket_file, temp_ticket)

    return None