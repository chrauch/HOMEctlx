# This file is part of HOMEctlx. Copyright (C) 2024 Christian Rauch.
# Distributed under terms of the GPL3 license.

"""
View-model for telemetry.
"""

from datetime import datetime
import subprocess
import services.meta as m
import services.fileaccess as fa
import services.dbaccess as dba
import services.authservice as auth


def ctl() -> list[m.view]:
    """ Starting point."""

    commands = list(map(lambda r: m.choice(r), routines()))

    return [
        m.view("_body", "telemetry", [
            user_info(),
            m.form("sh", "server health", [
                m.select_many("execute", commands, commands[:3]),
                m.execute("telemetry/health", "execute"),
                *health(routines()[:3]),
                m.space(2)
            ], False, True),
            logs()
        ])]


def user_info():
    """ Display user state and history."""
    current_user = auth.get_current_user()
    if not current_user:
        return m.form("ui", "user info", [m.label("Not authenticated")], False)
    
    # Get user details from database
    user = dba.get_user_by_name(current_user['uname'])
    if not user:
        return m.form("ui", "user info", [m.label("User not found")], False)
    
    # Get all state entries
    state_entries = dba.get_all_state_for_user(user['id'])
    
    # Build table rows for state
    state_rows = []
    for entry in state_entries:
        state_rows.append([
            m.label(entry['key']),
            m.label(entry['value'])
        ])
    
    fields = []
    
    # Add state table if there are entries
    if len(state_rows) > 0:
        state_table = m.table(rows=state_rows)
        fields.append(state_table)
        fields.append(m.space(2))
    else:
        fields.append(m.label("No state entries"))
        fields.append(m.space(2))
    
    # Add history
    history_text = user.get('history', 'No history available')
    fields.append(m.label(history_text, 'small'))
    
    return m.form("ui", "user info", fields, False)


def logs(open:bool=False):
    logs = fa.read_file(["temp", "logs"])
    return m.form("lo", "logs", [
                m.execute_params("telemetry/logs", "refresh", { 'open': True}),
                m.execute("telemetry/delete_logs", "clean",
                    confirm="Do you want to delete all log entries?"),
                m.text_big_ro("lo-l", logs)
            ], open, True)


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