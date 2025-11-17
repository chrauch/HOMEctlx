# This file is part of HOMEctlx. Copyright (C) 2024 Christian Rauch.
# Distributed under terms of the GPL3 license.

"""
Offers create, read, update, delete and more for the database.
"""

import datetime
import logging
import sqlite3
from sqlite3 import Error
from flask import g, has_request_context

log = logging.getLogger(__file__)


def init():
    """ Initializes the database."""
    execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            desc TEXT,
            start TEXT,
            state INTEGER)''', False)
    
    execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            password_saltedhash TEXT NOT NULL,
            permissions TEXT,
            description TEXT,
            history TEXT)''', False)
    
    execute('''
        CREATE TABLE IF NOT EXISTS state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userid INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT,
            FOREIGN KEY (userid) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(userid, key))''', False)


def connect():
    """ Open the connection."""
    dbaccess = sqlite3.connect("data.db", check_same_thread=False)
    dbaccess.row_factory = sqlite3.Row  # rows as dictionaries
    # Enable foreign key constraints
    dbaccess.execute("PRAGMA foreign_keys = ON")
    return dbaccess


init_dbaccess = None
def connect_cached():
    """ Get the connection."""
    if has_request_context():
        if 'dbaccess' in g: return g.dbaccess
        g.dbaccess = connect()
        return g.dbaccess
    else:
        global init_dbaccess
        if init_dbaccess == None: init_dbaccess = connect()
        return init_dbaccess


def close_cached():
    """ Close the connection."""
    if has_request_context():
        dbaccess = g.pop('dbaccess', None)
        if dbaccess is not None: dbaccess.close()
    else:
        global init_dbaccess
        init_dbaccess.close()
        init_dbaccess = None


def execute(sql:str, fetch:bool, data:tuple=()):
    """ Execute a single command."""
    try:
        connection = connect_cached()
        cursor = connection.cursor()
        cursor.execute(sql, data)
        if fetch: return cursor.fetchall()
        else:
            connection.commit()
            return cursor.lastrowid
    except Error as e: log.error(e)
    finally: 
        if cursor: cursor.close()
        #if connection: connection.close()
        # # closed in teardown_request


state_mapping = {
    'scheduled': 0,
    'running':   1,
    'completed': 2,
    'canceled':  3,
    'failed':    4,
    'unknown':   5,
}
state_mapping_reverse = {v: k for k, v in state_mapping.items()}
def get_tasks(states:list, types:list=None):
    """ Get tasks."""
    states_str = ",".join([str(state_mapping[s]) for s in states])
    sql = f"SELECT * FROM tasks WHERE state IN ({states_str})"
    if types != None:
        types_str = ",".join([f"'{t}'" for t in types])
        sql = f"{sql} AND type IN ({types_str})"
    tasks = execute(sql, True)
    return tasks


def clear_tasks(ids:list=None):
    """ Clear tasks."""
    sql = "DELETE FROM tasks"
    if ids == None: execute(sql, False)
    else: execute(f"{sql} WHERE id IN (?)", False, ([int(i) for i in ids]))


def add_task(type:str, desc:str, state:str='scheduled') -> int:
    """ Add task."""
    now = datetime.datetime.now()
    state = state_mapping[state]
    id = execute(
        """INSERT INTO tasks (type, desc, start, state) 
        VALUES (?, ?, ?, ?)""", False, 
        (type, desc, now, state))
    return id


def get_task_state(id:int):
    states = execute("SELECT state FROM tasks WHERE id = ?", True, tuple([id]))
    if len(states) == 0: return 'unknown'
    state = states[0]['state']
    state = state_mapping_reverse[state]
    return state


# User authentication functions
def get_user_by_name(name:str):
    """ Get user by username."""
    users = execute("SELECT * FROM users WHERE name = ?", True, (name,))
    if len(users) == 0: return None
    return dict(users[0])


def add_user(name:str, password_hash:str, permissions:str='user', description:str=''):
    """ Add a new user."""
    if len(name) < 1 or len(password_hash) < 1 or not name.isalnum() or name in ['admin', 'global']:
        log.error("Failed to add user: Name and password are required, and name must be alphanumeric, not 'admin' or 'global'")
        return None
    now = datetime.datetime.now().isoformat()
    history = f"{now}: Created"
    try:
        id = execute(
            """INSERT INTO users (name, password_saltedhash, permissions, description, history) 
            VALUES (?, ?, ?, ?, ?)""", False, 
            (name, password_hash, permissions, description, history))
        return id
    except Error as e:
        log.error(f"Failed to add user: {e}")
        return None


def update_user_history(name:str, action:str):
    """ Update user history, keeping only the last 100 lines."""
    user = get_user_by_name(name)
    if user:
        now = datetime.datetime.now().isoformat()
        new_entry = f"{now}: {action}"
        
        # Get existing history and split into lines
        history = user.get('history', '')
        lines = history.split('\n') if history else []
        
        # Add new entry
        lines.append(new_entry)
        
        # Keep only the last 100 lines
        if len(lines) > 100:
            lines = lines[-100:]
        
        # Join back into a single string
        history = '\n'.join(lines)
        execute("UPDATE users SET history = ? WHERE name = ?", False, (history, name))


def delete_user(name:str):
    """ Delete a user. State entries are automatically deleted via CASCADE."""
    user = get_user_by_name(name)
    if user:
        execute("DELETE FROM users WHERE name = ?", False, (name,))


def get_all_users():
    """ Get all users."""
    return execute("SELECT id, name, permissions, description, history FROM users", True)


# State management functions
def get_state_value(userid:int, key:str):
    """ Get a state value for a user."""
    result = execute("SELECT value FROM state WHERE userid = ? AND key = ?", True, (userid, key))
    if len(result) == 0: return None
    return result[0]['value']


def set_state_value(userid:int, key:str, value:str):
    """ Set a state value for a user. Creates or updates the entry."""
    # Try to update first
    execute("DELETE FROM state WHERE userid = ? AND key = ?", False, (userid, key))
    # Insert new value
    execute("INSERT INTO state (userid, key, value) VALUES (?, ?, ?)", False, (userid, key, value))


def get_all_state_for_user(userid:int):
    """ Get all state entries for a user."""
    return execute("SELECT key, value FROM state WHERE userid = ? ORDER BY key", True, (userid,))
