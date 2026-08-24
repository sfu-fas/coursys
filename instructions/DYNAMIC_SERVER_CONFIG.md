# The `/dynamic_config` Volume

This volume is mounted from `/data/dynamic_config` on the production server (and demo servers). In proddev, it's a docker volume accessible from the admin or manage containers.

It can contain a few files that let us dynamically control the system's behaviour...


## System-Wide Unavailable: `/dynamic_config/503`

If this file exists, it will put nginx into "503 unavailable" for all users.

Details: `docker/nginx/common.conf`.


## Healthcheck Verbosity: `/dynamic_config/healthcheck_errors`

If this exists, failing healthchecks (i.e. requests to `/healthcheck` by Docker) will cause exceptions and admin emails (as opposed to silent failure noticed only by Docker).

Details: `dashboard.views.healthcheck`.


## User Messages: `/dynamic_config/server_message.html` and `/dynamic_config/server_message_index.html`

These HTML fragments control the index-page and server-wide messages displayed for users, after signaling Gunicorn to notice the change.

Details: `instructions/SYSADMIN.md` "Server Messages" section.
