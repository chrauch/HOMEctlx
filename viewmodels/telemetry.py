# This file is part of HOMEctlx. Copyright (C) 2024 Christian Rauch.
# Distributed under terms of the GPL3 license.

"""
View-model for telemetry.
"""

from datetime import datetime
import subprocess
import services.meta as m
import services.fileaccess as fa


def ctl() -> list[m.view]:
    """ Starting point."""

    commands = list(map(lambda r: m.choice(r), routines()))

    return [
        m.view("_body", "telemetry", [
            m.form("sh", "server health", [
                m.select_many("execute", commands, commands[:3]),
                m.execute("telemetry/health", "execute"),
                *health(routines()[:3]),
                m.space(2)
            ], True, True),
            logs()
        ])]


def logs():
    logs = fa.read_file(["temp", "logs"])
    return m.form("lo", "logs", [
                m.execute("telemetry/delete_logs", "clean",
                    confirm="Do you want to delete all log entries?"),
                m.text_big_ro("lo-l", logs),
                m.autoupdate("telemetry/logs", 5000)
            ], False, False)


def health(execute:list):
    """ Execute routine."""
    results = list()
    for e in execute:
        if e not in routines(): raise Exception(f"'{e}' not allowed")
        try:
            result = subprocess.check_output(e, shell=True).decode("utf-8")
        except:
            result = "Error during execution."
        results.append(f"{e}\n\n{result}")
    out = "\n\n".join(results)
    return [m.text_big_ro("sh-r", out)]


def delete_logs():
    """ Deletes the logs."""
    fa.update_file(["temp", "logs"], f"Logs cleaned: {datetime.now()}\n", True)
    return [m.text_big_ro("lo-l", fa.read_file(["temp", "logs"]))]


def routines():
    """ Allowed routes."""
    return [
        "uname -a",
        "date",
        "uptime", 
        "lsb_release -a",
        "cat /etc/os-release",
        "lsmod",
        "systemctl status --no-pager",
        "lslogins",
        "who",
        "lscpu --all --extended",
        "cat /proc/cpuinfo",
        "cat /proc/meminfo",
        "lsusb -b",
        "ip addr",
        "ip route",
        "lsof -i",
        "nmap localhost",
        "netstat -tulna",
        "pstree",
        "ps aux",
        "lsblk",
        "iostat",
        "du -h",
        "df -h",
        "tree -h",
        "free -m",
        "sar -A",
        "journalctl --no-pager | tail -n 100"]