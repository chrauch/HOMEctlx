# This file is part of HOMEctlx. Copyright (C) 2024 Christian Rauch.
# Distributed under terms of the GPL3 license.

"""
State management service for persistent user preferences.
Stores state in both session (for quick access) and database (for persistence).
"""

import logging
from flask import session
import services.dbaccess as dba

log = logging.getLogger(__file__)


def _get_session_key(key: str) -> str:
    """Generate session key with prefix to avoid conflicts."""
    return f"state_{key}"


def get(key: str, default=None):
    """
    Get a state value for the current user.
    """
    session_key = _get_session_key(key)
    
    if session_key in session:
        return session[session_key]
    
    if 'uid' not in session:
        log.warning("Attempted to get state without authenticated user")
        return default
    
    userid = session['uid']
    value = dba.get_state_value(userid, key)
    
    if value is None: return default

    session[session_key] = value
    return value


def set(key: str, value):
    """
    Set a state value for the current user.
    """
    if 'uid' not in session:
        log.warning("Attempted to set state without authenticated user")
        return
    
    userid = session['uid']
    session_key = _get_session_key(key)
    
    value_str = str(value) if value is not None else ""

    session[session_key] = value_str

    dba.set_state_value(userid, key, value_str)
    #log.debug(f"Set state: {key}={value_str} for user {userid}")


def clear(key: str):
    """
    Clear a state value from both session and database.
    """
    if 'uid' not in session:
        return
    
    userid = session['uid']
    session_key = _get_session_key(key)

    session.pop(session_key, None)
    
    dba.execute("DELETE FROM state WHERE userid = ? AND key = ?", False, (userid, key))
    #log.debug(f"Cleared state: {key} for user {userid}")
