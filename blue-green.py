#!/usr/bin/env python

"""
Tool to manage switching between app-a and app-b backends, to allow graceful, safe deployments.

Note this is run outside of docker, on whatever Python version exists on the host.
"""

import argparse
import itertools
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import List


src_dir = Path("/coursys/docker/nginx/backend-configs")
dest = Path("/dynamic_config/nginx-backends.conf")


def run(cmd: List[str]):
    res = subprocess.run(cmd)
    if res.returncode != 0:
        raise RuntimeError(res)


def dc_run(container: str, command: List[str]):
    """
    docker compose run [container] [command]
    """
    run(["docker", "compose", "run", "-q", "--remove-orphans"] + [container] + command)


def nginx_reload():
    """
    Tell the nginx container to gracefully reload its config files.
    """
    run(["docker", "compose", "kill", "--remove-orphans", "-s", "SIGHUP", "nginx"])


def use_config(name: str):
    """
    Use the nginx backend config {name}.conf.
    """
    config_file = Path(src_dir / f"{name}.conf")
    dc_run("admin", ["cp", config_file, dest])
    nginx_reload()


def do_actions(actions: List[str]):
    """
    Run each requested action *and* wait long enough for each to take effect before moving on.
    """
    for action in actions:
        match_drain = re.match(r"^drain-(.)$", action)
        match_up = re.match(r"^up-(.)$", action)
        if action == "show":
            dc_run("admin", ["cat", dest])
            print()
        elif action == "build":
            run(["make", "build"])
        elif action == "defaults":
            use_config("default")
            time.sleep(1)
        elif action == "all-up":
            run(["docker", "compose", "up", "-d", "--wait"])
            time.sleep(1)
        elif match_drain:
            use_config(action)
            time.sleep(5)
        elif match_up:
            instance = match_up.group(1)
            run(["docker", "compose", "up", "-d", "--wait", f"app-{instance}"])
            time.sleep(1)
        elif action == "reload":
            do_actions(["build", "drain-a", "up-a", "drain-b", "up-b", "defaults", "all-up"])
        else:
            raise NotImplementedError()


def main(argv):
    backends = ["a", "b"]
    actions = list(
        itertools.chain.from_iterable(
            [f"drain-{instance}", f"up-{instance}"] for instance in backends
        )
    ) + ["show", "build", "defaults", "all-up", "reload"]
    parser = argparse.ArgumentParser("Blue-green app manager")
    parser.add_argument(
        "actions",
        nargs="*",
        choices=actions,
        help="actions to perform (in the order given)",
    )
    args = parser.parse_args(argv)
    do_actions(args.actions)


main(sys.argv[1:])
