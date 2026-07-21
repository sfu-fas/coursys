import os
import pathlib

from django.template import Template, Context


# The context variables passed into the docker/compose-template.yml template:
# "data_location":   prefix for docker mounts: directory or "" for pure docker volumes
# "uid":             the UID for the coursys user in containers: must match any external files that already exist, else is arbitrary.
# "external_port":   the port where nginx should listen for HTTP requests
# "selinux":         do we need the selinux "z" options for docker bind mounts?
# "serve_hosts":     hostnames where we serve the actual site
# "redirect_hosts":  old hostnames that forward to the canonical host
# "canonical_name":  the canonical location to forward users to if they come from somewhere besides a serve_host
# "user_protocol":   the protocol (http or https) that is visibile to users (for correct redirects)
# "user_port":       the TCP port the user connects to (for correct redirects and CSRF checks)
# "app_replicas":    number of replicas of the app container
# "dev_services":    start mysql and smtp4dev for non-production use?
# "service_secrets": do we use the ./secrets/ files with rabbitmq and elasticsearch passwords?

# URLs that users go to must match f"{user_protocol}://{a_serve_host}:{user_port}/"
# Used in nginx config to server/forward domains as relevant, and in Django config for ALLOWED_HOSTS
# and CSRF_TRUSTED_ORIGINS.


DEPLOYMENT_CONTEXTS = {
    "proddev": {  # config for devs to make things easy to set up but also very much like production
        "data_location": "",  # i.e. in docker volumes
        "uid": 888,
        "external_port": 8080,
        "selinux": False,
        "serve_hosts": "localhost",
        "redirect_hosts": "olddomain",
        "canonical_name": "localhost",
        "user_protocol": "http",
        "user_port": 8080,
        "app_replicas": 1,
        "dev_services": True,
        "service_secrets": False,  # don't bother, for simpler dev setup
    },
    "demo": {  # config for a demo server, and also as close to prod as possible
        "data_location": "/data/",
        "uid": 888,
        "external_port": 80,
        "selinux": True,
        "serve_hosts": "coursys-demo.selfip.net coursys-test.selfip.net localhost",
        "redirect_hosts": "olddomain",
        "canonical_name": "coursys-demo.selfip.net",
        "user_protocol": "http",
        "user_port": 80,
        "app_replicas": 2,
        "dev_services": True,
        "service_secrets": True,
    },
    "production": {  # true prodution setup
        "data_location": "/data/",
        "uid": 6501,
        "external_port": 80,
        "selinux": True,
        "serve_hosts": "coursys.sfu.ca fasit.sfu.ca",
        "redirect_hosts": "coursys.cs.sfu.ca courses.cs.sfu.ca",
        "canonical_name": "coursys.sfu.ca",
        "user_protocol": "https",
        "user_port": 443,
        "app_replicas": 2,
        "dev_services": False,
        "service_secrets": True,
    },
}

PREFIX = """# This file is generated from docker/compose-template.yml and "manage.py build_compose_yml".
# Edit the template, not this file. Definitely don't check in any edits.
"""


def build_from_template(deploy_mode: str) -> str:
    """
    Construct the compose.yml file for the given deployment mode.
    """
    ctx = DEPLOYMENT_CONTEXTS[deploy_mode]
    ctx["deploy_mode"] = deploy_mode
    data_location = ctx["data_location"]
    assert data_location == "" or data_location.endswith(
        "/"
    ), "data_location directory must end with a slash"
    ctx["everything_in_docker_volumes"] = data_location == ""

    template_location = (
        pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
        / "compose-template.yml"
    )

    context = Context(ctx)
    template = Template(open(template_location, "rt", encoding="utf-8").read())
    content = template.render(context)
    return PREFIX + content
