# This file is part of HOMEctlx. Copyright (C) 2024 Christian Rauch.
# Distributed under terms of the GPL3 license.

"""
View-model for alarms and timers.
"""

from datetime import datetime, timedelta
import json
import services.lightctlwrapper as lw
import services.scheduler as sd
from services.lightstates import States
import services.meta as m
import services.state as state


def ctl() -> list[m.view]:
    """ Starting point."""

    states_txt = lw.exec(f"state", brief=False)
    states = States('\n'.join(states_txt.split('\n')[1:]))
    names = sorted([s.name for s in states.items])

    # Load saved preferences from state
    saved_devices_json = state.get('alarms.devices', '[]')
    try:
        saved_devices_names = json.loads(saved_devices_json)
    except:
        saved_devices_names = []
    
    saved_timer_minutes = int(state.get('alarms.timer_minutes', 10))
    
    saved_alarm_time = state.get('alarms.alarm_time')
    if saved_alarm_time:
        default_time = saved_alarm_time
    else:
        default = datetime.now() + timedelta(hours=8)
        default_time = default.time().strftime("%H:%M")

    # Convert saved device names to choice objects for select_many
    all_choices = list(map(lambda d: m.choice(d), names))
    saved_devices_choices = [c for c in all_choices if c.value in saved_devices_names]
    
    select_devices = m.select_many("devices", \
        all_choices, saved_devices_choices, "devices")

    now = f"Server time:\n{datetime.now().strftime('%Y-%m-%d %H:%M')}"

    forms = [*scheduled()]
    
    # timer
    #mins = [*range(1, 20, 1), *range(20, 60, 5), *range(60, 241, 10)]
    forms.append(
        m.form("timer", "set", [
            select_devices,
            m.space(2),
            m.integer("minutes", saved_timer_minutes, "set timer (minutes)"),
            #m.select("minutes", list(map(lambda i: m.choice(i), mins)), None, "set timer (minutes)"),
            m.execute_params("alarms/set", "set", {"method" : "timer"}),
            m.space(2),
            m.time("time", default_time, "set alarm (hh:mm)"),
            m.execute_params("alarms/set", "set", {"method" : "alarm"}),
        ], True))
    
    return [m.view("_body", "timers and alarms", forms)]


def set(method:str, time:str, minutes:int, devices:list[str]):
    if len(devices) == 0: return [m.error("Select at least one device.")]
    
    # Save preferences to state
    state.set('alarms.devices', json.dumps(devices))
    state.set('alarms.timer_minutes', int(minutes))
    state.set('alarms.alarm_time', time)
    
    if method == 'timer': _set_timer(int(minutes), devices)
    else: _set_alarm(time, devices)
    return scheduled()


def _set_alarm(time, devices:list[str]):
    """ Alarm."""
    current_time = datetime.now().time()
    target_time = datetime.strptime(time, "%H:%M").time()
    today = datetime.today()
    target_datetime = datetime.combine(today, target_time)
    # next day
    if target_time < current_time: target_datetime += timedelta(days=1)
    time_difference = target_datetime \
        - datetime.combine(today, current_time)
    minutes = time_difference.total_seconds() / 60
    return _set_timer(minutes, devices, True)


def _set_timer(minutes:int, devices:list[str], alarm:bool=False):
    """ Set timer."""
    now = datetime.now()
    target = now + timedelta(minutes=minutes)
    names_str = ", ".join((sorted(devices)))
    min = '' if alarm else f" ({minutes} min.)"
    desc = f"{target.strftime('%Y-%m-%d %H:%M')}{min} on {names_str}"
    def _blink(): lw.blink(devices)
    sd.execute_delayed_background(
        target, _blink, 'timer' if not alarm else 'alarm', desc)
    return scheduled()


def scheduled(stop:str=None):
    """ Schedules a timer."""
    if stop != None: sd.terminate(stop)
    all = sd.all()
    timers_alarms = [t for t in all if t['type'] in ['timer', 'alarm']]
    rest = [t for t in all if t not in timers_alarms]
    def _desc(r): return f"{r['type']}: {r['desc']}"
    tasks = list(map(lambda r: m.choice(r['id'], _desc(r)), timers_alarms))
    triggers = m.triggers("alarms/scheduled", "stop", tasks, \
            confirm="Do you want to delete this timer/alarm?") \
        if len(tasks) > 0 else m.label("no timers and no alarms")
    labels = labels = [m.label(_desc(t), 'small') for t in rest] \
        if len(rest) > 0 else []
    return [m.form("scheduled", "running", [
        triggers, *labels, m.autoupdate("alarms/scheduled", 5000)], True)]