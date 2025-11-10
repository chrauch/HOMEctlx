# This file is part of HOMEctlx. Copyright (C) 2024 Christian Rauch.
# Distributed under terms of the GPL3 license.

"""
Calendar manager for reading and managing calendar events.
"""

import os
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from flask import session
import services.fileaccess as fa


log = logging.getLogger(__file__)


@dataclass
class CalendarEvent:
    """Represents a calendar event."""
    date: datetime
    description: str
    source: str  # 'global' or username
    recurring: str = None  # None, 'yearly', 'monthly', 'weekly'
    
    def __lt__(self, other):
        """Enable sorting by date."""
        return self.date < other.date


def parse_event_line(line: str, source: str) -> CalendarEvent:
    """
    Parse a calendar event line.
    Format: 2025-01-01 New Year's Day
    Format with recurrence: 2025-01-01[yearly] New Year's Day
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    
    try:
        # Check for recurrence marker
        recurring = None
        if '[' in line and ']' in line:
            # Extract recurrence type
            start_bracket = line.index('[')
            end_bracket = line.index(']')
            recurring = line[start_bracket+1:end_bracket].lower()
            # Remove the bracket part from the line
            line = line[:start_bracket] + line[end_bracket+1:]
        
        # Split date and description
        parts = line.split(maxsplit=1)
        if len(parts) < 2:
            return None
        
        date_str = parts[0].strip()
        description = parts[1].strip()
        
        # Parse date
        date = datetime.strptime(date_str, "%Y-%m-%d")
        
        return CalendarEvent(
            date=date,
            description=description,
            source=source,
            recurring=recurring
        )
    except Exception as e:
        log.warning(f"Failed to parse calendar line '{line}': {e}")
        return None


def expand_recurring_event(event: CalendarEvent, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
    """
    Expand a recurring event into multiple events within the date range.
    """
    if not event.recurring:
        # Non-recurring event: only return if within range
        if start_date <= event.date <= end_date:
            return [event]
        else:
            return []
    
    events = []
    current_date = event.date
    max_iterations = 10000  # Safety limit to prevent infinite loops
    iteration_count = 0
    
    # Start from the first occurrence within or after start_date
    while current_date < start_date and iteration_count < max_iterations:
        iteration_count += 1
        if event.recurring == 'yearly':
            try:
                current_date = current_date.replace(year=current_date.year + 1)
            except ValueError:
                # Handle leap year edge case (Feb 29)
                current_date = current_date.replace(year=current_date.year + 1, day=28)
        elif event.recurring == 'monthly':
            # Add one month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                # Handle month-end edge cases
                try:
                    current_date = current_date.replace(month=current_date.month + 1)
                except ValueError:
                    # Day doesn't exist in next month (e.g., Jan 31 -> Feb 31)
                    # Move to last day of next month
                    next_month = current_date.month + 1
                    next_year = current_date.year
                    if next_month > 12:
                        next_month = 1
                        next_year += 1
                    # Find last day of next month
                    if next_month == 12:
                        last_day = 31
                    else:
                        from calendar import monthrange
                        last_day = monthrange(next_year, next_month)[1]
                    current_date = current_date.replace(year=next_year, month=next_month, day=last_day)
        elif event.recurring == 'weekly':
            current_date = current_date + timedelta(days=7)
        else:
            # Unknown recurrence type, treat as non-recurring
            log.warning(f"Unknown recurrence type: {event.recurring}")
            if start_date <= event.date <= end_date:
                return [event]
            else:
                return []
    
    # Generate occurrences within the date range
    iteration_count = 0
    while current_date <= end_date and iteration_count < max_iterations:
        iteration_count += 1
        events.append(CalendarEvent(
            date=current_date,
            description=event.description,
            source=event.source,
            recurring=event.recurring
        ))
        
        # Move to next occurrence
        if event.recurring == 'yearly':
            try:
                current_date = current_date.replace(year=current_date.year + 1)
            except ValueError:
                # Handle leap year edge case (Feb 29)
                current_date = current_date.replace(year=current_date.year + 1, day=28)
        elif event.recurring == 'monthly':
            # Add one month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                # Handle month-end edge cases
                try:
                    current_date = current_date.replace(month=current_date.month + 1)
                except ValueError:
                    # Day doesn't exist in next month
                    next_month = current_date.month + 1
                    next_year = current_date.year
                    if next_month > 12:
                        next_month = 1
                        next_year += 1
                    # Find last day of next month
                    if next_month == 12:
                        last_day = 31
                    else:
                        from calendar import monthrange
                        last_day = monthrange(next_year, next_month)[1]
                    current_date = current_date.replace(year=next_year, month=next_month, day=last_day)
        elif event.recurring == 'weekly':
            current_date = current_date + timedelta(days=7)
        else:
            break
    return events


def read_calendar_file(file_path: str, source: str) -> list[CalendarEvent]:
    """Read and parse a single calendar file."""
    try:
        content = fa.read_file(file_path.split('/'), default="")
        if not content:
            return []
        
        events = []
        for line in content.split('\n'):
            event = parse_event_line(line, source)
            if event:
                events.append(event)
        
        return events
    except Exception as e:
        log.error(f"Error reading calendar file {file_path}: {e}")
        return []


def get_events(start_date: datetime = None, end_date: datetime = None, days_ahead: int = 30) -> list[CalendarEvent]:
    """
    Get all calendar events within the specified date range.
    
    Args:
        start_date: Start date for the range (default: today)
        end_date: End date for the range (default: start_date + days_ahead)
        days_ahead: Number of days to look ahead if end_date not specified
    
    Returns:
        Sorted list of calendar events
    """
    if start_date is None:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if end_date is None:
        end_date = start_date + timedelta(days=days_ahead)
    
    all_events = []
    
    # Read global calendar files
    global_dir = ['calendar', 'global']
    try:
        files, _ = fa.list_files(global_dir)
        for file_name in files:
            if file_name.endswith('.calx'):
                file_path = '/'.join(global_dir + [file_name])
                events = read_calendar_file(file_path, 'global/' + file_name[:-5])
                all_events.extend(events)
    except Exception as e:
        log.warning(f"Could not read global calendar directory: {e}")
    
    # Read user-specific calendar files
    if 'uname' in session:
        username = session['uname']
        user_dir = ['calendar', username]
        
        # Create user directory if it doesn't exist
        try:
            user_dir_path = fa.share_path(user_dir)
            if not os.path.exists(user_dir_path):
                fa.create_directory(user_dir)
                fa.create_file(['calendar', username, 'schedule.calx'], "")
                log.info(f"Created user calendar directory: {username}")
        except Exception as e:
            log.warning(f"Could not create user calendar directory: {e}")
        
        # Read user calendar files
        try:
            files, _ = fa.list_files(user_dir)
            for file_name in files:
                if file_name.endswith('.calx'):
                    file_path = '/'.join(user_dir + [file_name])
                    events = read_calendar_file(
                        file_path, username + '/' + file_name[:-5])
                    all_events.extend(events)
        except Exception as e:
            log.warning(f"Could not read user calendar directory: {e}")
    
    # Expand recurring events
    expanded_events = []
    for event in all_events:
        expanded_events.extend(expand_recurring_event(event, start_date, end_date))
    
    # Filter events within date range and sort
    filtered_events = [e for e in expanded_events if start_date <= e.date <= end_date]
    filtered_events.sort()
    
    return filtered_events


def format_event(event: CalendarEvent) -> dict:
    """Format an event for display."""
    recurring_marker = f"[{event.recurring}]" if event.recurring else ""
    return {
        'date': event.date.strftime('%Y-%m-%d'),
        'weekday': event.date.strftime('%A'),
        'description': event.description,
        'source': event.source,
        'recurring': recurring_marker
    }


def get_calendar_files() -> dict:
    """
    Get all calendar file paths for global and current user.
    
    Returns:
        Dictionary with 'global' and 'user' keys containing lists of file paths
    """
    calendar_files = {
        'global': [],
        'user': []
    }
    
    # Get global calendar files
    global_dir = ['calendar', 'global']
    try:
        files, _ = fa.list_files(global_dir)
        for file_name in files:
            if file_name.endswith('.calx'):
                # Return path relative to share directory for applink
                calendar_files['global'].append(['calendar', 'global', file_name])
    except Exception as e:
        log.warning(f"Could not read global calendar directory: {e}")
    
    # Get user-specific calendar files
    if 'uname' in session:
        username = session['uname']
        user_dir = ['calendar', username]
        
        # Create user directory if it doesn't exist
        try:
            user_dir_path = fa.share_path(user_dir)
            if not os.path.exists(user_dir_path):
                fa.create_directory(user_dir)
                fa.create_file(['calendar', username, 'schedule.calx'], "")
                log.info(f"Created user calendar directory: {username}")
        except Exception as e:
            log.warning(f"Could not create user calendar directory: {e}")
        
        # Read user calendar files
        try:
            files, _ = fa.list_files(user_dir)
            for file_name in files:
                if file_name.endswith('.calx'):
                    calendar_files['user'].append(['calendar', username, file_name])
        except Exception as e:
            log.warning(f"Could not read user calendar directory: {e}")
    
    return calendar_files
