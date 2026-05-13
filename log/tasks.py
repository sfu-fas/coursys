import datetime
import json
import os
import shutil
import subprocess
import psutil
from django.db.models import Avg, Count

from courselib.celerytasks import task
from log.models import MonitoringDataLog, RequestLog


# sort out the docker executables
docker = ["docker"]
if shutil.which("docker-compose"):
    docker_compose = ["docker-compose", "-f", "./docker-compose.yml"]
else:
    docker_compose = ["docker", "compose", "-f", "./docker-compose.yml"]


@task(queue="batch")
def log_regular():
    """
    Logging we want to do regularly: every ~15 minutes.
    """
    log_system_usage()
    log_process_usage()
    log_container_usage()


@task(queue="batch")
def log_system_usage():
    """
    Log system load and memory usage.
    """
    now = datetime.datetime.now()
    load = psutil.getloadavg()
    vm = psutil.virtual_memory()

    MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric="load_1",
        value=load[0],
        data={},
    ).save()
    MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric="load_5",
        value=load[1],
        data={},
    ).save()
    MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric="load_15",
        value=load[2],
        data={},
    ).save()
    MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric="mem_avail_gb",
        value=vm.available / 1e9,
        data={},
    ).save()


def log_container(name: str):
    """
    Log information about a single docker container with this docker-compose name.
    """
    now = datetime.datetime.now()
    try:
        id = subprocess.check_output(docker_compose + ["ps", "-q", name]).strip()
        stats_json = subprocess.check_output(
            docker + ["stats", "--no-stream", "--format", "json", id]
        ).strip()
    except subprocess.CalledProcessError:
        MonitoringDataLog(
            time=now,
            duration=datetime.timedelta(seconds=0),
            metric=f"{name}_is_missing",
            value=0,
            data={},
        ).save()
        return

    stats = json.loads(stats_json)

    cpu = float(stats["CPUPerc"].replace("%", ""))
    mem = float(stats["MemPerc"].replace("%", ""))
    ps = int(stats["PIDs"])
    MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric=f"{name}_mem_percent",
        value=mem,
        data={},
    ).save()
    MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric=f"{name}_cpu_percent",
        value=cpu,
        data={},
    ).save()
    MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric=f"{name}_n_procs",
        value=ps,
        data={},
    ).save()


@task(queue="batch")
def log_container_usage():
    """
    Log resources used by each of our Docker containers.
    """
    log_container("rabbitmq")
    log_container("elasticsearch")
    log_container("memcached")


def log_process(name: str, pid: int):
    now = datetime.datetime.now()
    process = psutil.Process(pid=pid)
    with process.oneshot():
        cpu = process.cpu_percent()
        vm = process.memory_info().vms
        ps = 1

        for p in process.children(recursive=True):
            with p.oneshot():
                cpu += p.cpu_percent()
                vm += p.memory_info().vms
                ps += 1

    MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric=f"{name}_mem_used_mb",
        value=vm / 1e6,
        data={},
    ).save()
    MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric=f"{name}_cpu_percent",
        value=cpu,
        data={},
    ).save()
    MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric=f"{name}_n_procs",
        value=ps,
        data={},
    ).save()


def service_info(name: str):
    """
    Log resources used by systemd service (and all child processes).
    """
    service_pid = int(
        subprocess.check_output(
            ["systemctl", "show", "--property", "MainPID", "--value", name]
        ).strip()
    )
    if service_pid == 0:
        MonitoringDataLog(
            time=datetime.datetime.now(),
            duration=datetime.timedelta(seconds=0),
            metric=f"{name}_is_down",
            value=0,
            data={},
        ).save()
    else:
        log_process(name, service_pid)


def log_celery():
    # the way celery services get forked requires special handling
    pid_path = "/opt/run/celery/"
    for pidfile in os.listdir(pid_path):
        pid = int(open(os.path.join(pid_path, pidfile), "rt", encoding="ascii").read())
        name = pidfile.split(".")[0]
        log_process(f"celery_{name}", pid)


@task(queue="batch")
def log_process_usage():
    service_info("gunicorn")
    service_info("nginx")
    # don't bother with celery for now: can enable if it seems worth watching
    # service_info("celerybeat")
    # log_celery()


@task(queue="batch")
def log_avg_request_duration():
    """
    Log average time needed to respond to HTTP requests (by Django, over the last hour).
    """
    now = datetime.datetime.now()
    agg = RequestLog.objects.filter(
        time__gte=now - datetime.timedelta(hours=1)
    ).aggregate(duration=Avg("duration"), count=Count("*"))
    avg = agg["duration"]
    count = agg["count"]
    MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric="requests_hourly_count",
        value=count,
        data={},
    ).save()
    if avg is not None:
        MonitoringDataLog(
            time=now,
            duration=datetime.timedelta(seconds=0),
            metric="requests_hourly_duration_avg_ms",
            value=avg.total_seconds() * 1000,
            data={},
        ).save()
