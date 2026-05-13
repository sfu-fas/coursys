import datetime
import json
import os
import subprocess
import psutil
from django.db.models import Avg, Count

from courselib.celerytasks import task
from log.models import MonitoringDataLog, RequestLog


@task(queue="batch")
def log_all():
    log_system_usage()
    log_avg_request_duration()
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
    print(vm)

    log = MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric="load_1",
        value=load[0],
        data={},
    )
    log.save()
    log = MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric="load_5",
        value=load[1],
        data={},
    )
    log.save()
    log = MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric="load_15",
        value=load[2],
        data={},
    )
    log.save()
    log = MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric="mem_avail_gb",
        value=vm.available / 1e9,
        data={},
    )
    log.save()


docker = ["docker"]
docker_compose = ["docker-compose", "-f", "/coursys/docker-compose.yml"]


def log_container(name: str):
    id = subprocess.check_output(docker_compose + ["ps", "-q", name]).strip()
    stats_json = subprocess.check_output(
        docker + ["stats", "--no-stream", "--format", "json", id]
    ).strip()
    stats = json.loads(stats_json)
    now = datetime.datetime.now()

    cpu = float(stats["CPUPerc"].replace("%", ""))
    mem = float(stats["MemPerc"].replace("%", ""))
    ps = int(stats["PIDs"])
    log = MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric=f"{name}_mem_percent",
        value=mem,
        data={},
    )
    log.save()
    log = MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric=f"{name}_cpu_percent",
        value=cpu,
        data={},
    )
    log.save()
    log = MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric=f"{name}_n_procs",
        value=ps,
        data={},
    )
    log.save()


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

    log = MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric=f"{name}_mem_used_mb",
        value=vm / 1e6,
        data={},
    )
    log.save()
    log = MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric=f"{name}_cpu_percent",
        value=cpu,
        data={},
    )
    log.save()
    log = MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric=f"{name}_n_procs",
        value=ps,
        data={},
    )
    log.save()


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
        log = MonitoringDataLog(
            time=datetime.datetime.now(),
            duration=datetime.timedelta(seconds=0),
            metric=f"{name}_is_down",
            value=0,
            data={},
        )
        log.save()
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
    service_info("celerybeat")
    service_info("nginx")
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
    log = MonitoringDataLog(
        time=now,
        duration=datetime.timedelta(seconds=0),
        metric="request_count_hourly",
        value=count,
        data={},
    )
    log.save()
    if avg is not None:
        log = MonitoringDataLog(
            time=now,
            duration=datetime.timedelta(seconds=0),
            metric="request_duration_avg_hourly_ms",
            value=avg.total_seconds() * 1000,
            data={},
        )
        log.save()
