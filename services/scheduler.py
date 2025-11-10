# This file is part of HOMEctlx. Copyright (C) 2024 Christian Rauch.
# Distributed under terms of the GPL3 license.

"""
Schedules tasks, will spawn threads and handles cancellation.
"""

from datetime import datetime
import logging
import sched
from threading import Thread
import time
from typing import Callable
from flask import session


log = logging.getLogger(__file__)


def init(dbaccess):
    """ Sets the dbaccess."""
    global dba
    dba = dbaccess
    tasks = all()
    if len(tasks) > 0:
        tasks = [f"{t['id']} [{t['state']} / {t['start']}] {t['desc']}" \
            for t in tasks]
        log.warning(f"Tasks: {'; '.join(tasks)}")
    dba.clear_tasks()


def all():
    """ All tasks."""
    return dba.get_tasks(dba.state_mapping.keys())


def execute_delayed_background(
    datetime:datetime, func:Callable, type:str, desc:str):
    """ Delays an execution (not blocking)."""
    Thread(target=execute_delayed, args=[datetime, func, type, desc]).start()


def execute_delayed(datetime:datetime, func:Callable, type:str, desc:str):
    """ Delays an execution (blocking)."""
    id = dba.add_task(type, desc)
    def _run():
        if dba.get_task_state(id) != 'scheduled': 
            log.info(f"Task '{id}' got terminated before it ran.")
            return
        try:    func()
        except: log.error(f"Task '{id}' not successfully completed.")
        terminate(id)
        log.info(f"Task '{desc}' marked as terminated.")
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler.enterabs(datetime.timestamp(), 1, _run)
    scheduler.run(blocking=True)
    log.info(f"Task '{desc}' got scheduled for {datetime}.")


def terminate(id):
    """ Terminate the task."""
    dba.clear_tasks([id])
    log.info(f"Task '{id}' terminated.")
