# This file is part of HOMEctlx. Copyright (C) 2024 Christian Rauch.
# Distributed under terms of the GPL3 license.

"""
Call lightctl to set device states (such as hue or brightness).
"""

import logging
import subprocess
import time
import copy
from services.lightstates import State, States, Group


log = logging.getLogger(__file__)
executable = None


def init(configured_executable):
    """ Wraps the lightctl executable."""
    global executable
    executable = configured_executable


def exec(cmd, type = "dev", parameters = "", brief = True) -> str:
    """ Executes the wrapped LightCtl command."""
    if type == "grp":    cmd += "-group"
    if parameters != "": cmd += " " + parameters
    full_cmd = f"{executable} {cmd} {'--brief' if brief else ''}"
    
    try:
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            log.error(f"Lightctl command failed: {full_cmd}")
            log.error(f"Return code: {result.returncode}")
            log.error(f"STDOUT: {result.stdout}")
            log.error(f"STDERR: {result.stderr}")
            raise subprocess.CalledProcessError(
                result.returncode, 
                full_cmd, 
                output=result.stdout, 
                stderr=result.stderr
            )
        
        return result.stdout
        
    except subprocess.TimeoutExpired as e:
        log.error(f"Lightctl command timeout: {full_cmd}")
        log.error(f"Timeout after 30 seconds")
        raise
    except FileNotFoundError as e:
        log.error(f"Lightctl executable not found: {executable}")
        log.error(f"Error: {str(e)}")
        raise
    except Exception as e:
        log.error(f"Unexpected error executing lightctl: {str(e)}")
        log.error(f"Exception type: {type(e).__name__}")
        raise


def state(type, id) -> State:
    """ Gets the state of the device or group."""
    return State(exec("state", type, id))


def states(groups:True=False) -> list[State]:
    """ Gets the states."""
    type = "grp" if groups else "dev"
    return States(exec(f"state", type)).items


def set_attributes(ids:list[str], attr:str, val:str):
    """ Sets an attribute of a device or group."""
    if attr not in ["pwr", "hue", "sat", "bri"]:
        raise Exception("Invalid attribute")
    for id in ids:
        state = State(exec("state", 'dev', id))
        if attr == "pwr":
            if val != "on" and val != "off": raise Exception("Invalid value")
            setattr(state, "pwr", val)
        else:
            pwr = "off" if attr == "bri" and int(val) < 1 else "on"
            setattr(state, attr, int(val))
            setattr(state, "pwr", pwr)
        exec("set", type, state.str())


def set_state(state:State):
    """ Sets the state."""
    exec("set", "", state.str())


def set_states(states:list[State], ids:set[str]):
    """ Sets the states."""
    for s in states:
        if s.id not in ids: continue
        s_on = copy.deepcopy(s)
        s_on.pwr = "on"
        set_state(s_on)
        set_state(s)


def get_ids_in_group(group_id):
    """ Gets the IDs of group members."""
    ids = State(exec("state", "grp", group_id)).memids
    return ids


def set_all_off():
    """ Turns all lights off."""
    states = States(exec("state")).items
    for s in states:
        if s.pwr == "off": continue
        s.pwr = "off"
        exec("set", "", s.str())


def states_grouped(type:str) -> list[Group]:
    """ Gets the device or group states."""
    groups = list()

    states_dev = States(exec("state", "dev"))

    if type == "grp":
    
        states_grp = States(exec("state", "grp"))

        for state_grp in sorted(states_grp.items, key=lambda g: g.name):

            states_mem = states_dev.get_subset(
                lambda s: (s.id in state_grp.memids))

            for attr in ["bri", "sat", "hue"]:

                values = [s.__dict__[attr] for s in states_mem.items]
                values = [int(v) for v in values if v != None and v != "-"]

                value = "-" if len(values) == 0 \
                            else str(int(sum(values) / len(values)))

                state_grp.__dict__[attr] = value

            state_grp.has_sat = any(m.has_sat for m in states_mem.items)
            state_grp.has_hue = any(m.has_hue for m in states_mem.items)

            state_grp.pwr = "on" \
                if any(m.pwr == "on" for m in states_mem.items) \
                else "off"
            
            groups.append(Group(state_grp, states_mem))

    else:
        head = dict()
        head["name"] = ""
        groups.append(Group(head, states_dev))
    
    return groups


def blink(names:list[str]):
    """ Lets the devices blink after a delay."""
    states = States(exec("state")).items
    for state in states:
        if state.name not in names: continue
        for _ in range(3):
            # set alarm state temporarily
            pwr = state.pwr
            state_alarm = copy.deepcopy(state)
            state_alarm.pwr = "on"
            state_alarm.sat = 100
            state_alarm.bri = 100
            state_alarm.hue = 0
            set_state(state_alarm)
            time.sleep(1)
            # reset device (pwr needs to be on)
            state.pwr = "on"
            set_state(state)
            time.sleep(0.1)
            state.pwr = pwr
            set_state(state)

