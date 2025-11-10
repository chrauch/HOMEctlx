# This file is part of HOMEctlx. Copyright (C) 2024 Christian Rauch.
# Distributed under terms of the GPL3 license.

"""
View-model for calendar events.
"""

from datetime import datetime, timedelta
import services.calmgr as cm
import services.meta as m


def ctl() -> list[m.view]:
    """Starting point."""
    return [m.view("_body", "calendar", [*overview(), *edit()])]


def edit() -> list[m.form]:
    """
    Edit calendar files.
    """
    calendar_files = cm.get_calendar_files()
    
    fields = []

    def path_str(file_path):
        return " > ".join(file_path[1:]).replace('.calx', '')
    
    # Global calendar files
    if calendar_files['global']:
        for file_path in calendar_files['global']:
            file_name = file_path[-1]
            # Create query string for files viewmodel
            dir_path = '/'.join(file_path[:-1])
            link = f"/files/ctl?dir={dir_path}&file={file_name}"
            fields.append(m.applink(link, "edit", path_str(file_path)))
    else:
        fields.append(m.label("No global calendar files found", "info"))
    
    # User calendar files
    if calendar_files['user']:
        for file_path in calendar_files['user']:
            file_name = file_path[-1]
            dir_path = '/'.join(file_path[:-1])
            link = f"/files/ctl?dir={dir_path}&file={file_name}"
            fields.append(m.applink(link, "edit", path_str(file_path)))
    else:
        fields.append(m.label("No user calendar files yet", "info"))
    
    # Instructions
    fields.append(m.label("Create new .calx files in your calendar directory to add personal events", "info small"))
    
    return [m.form("edit", "edit", fields, open=True)]


def overview(start_date: str = None, end_date: str = None) -> list[m.form]:
    """
    Display overview of events in a date range.
    """
    # Convert string dates if provided
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start = today + timedelta(days=0)
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end = start + timedelta(days=90)  # 3 months from start
    
    # Get events
    events = cm.get_events(start, end)
    
    # Date range controls
    default_start = start.strftime("%Y-%m-%d")
    default_end = end.strftime("%Y-%m-%d")
    
    controls = [
        m.text("start_date", default_start, "from"),
        m.text("end_date", default_end, "to"),
        m.execute_params("calendar/overview", "refresh", {})
    ]
    
    # Group events by date
    events_by_date = {}
    for event in events:
        date_key = event.date.strftime('%Y-%m-%d %A')[0:14]
        if date_key not in events_by_date:
            events_by_date[date_key] = []
        events_by_date[date_key].append(event)
    
    # Create fields
    fields = controls
    
    if len(events) == 0:
        fields.append(m.label("No events in this period", "info"))
    else:
        # Add event count summary
        total_events = len(events)
        unique_dates = len(events_by_date)
        summary = f"{total_events} event{'s' if total_events != 1 else ''} on {unique_dates} day{'s' if unique_dates != 1 else ''}"
        fields.append(m.label(summary, "info small"))
        fields.append(m.space(1))
        
        # List events grouped by date
        for date_key in sorted(events_by_date.keys()):
            date_events = events_by_date[date_key]
            first_event = date_events[0]
            
            fields.append(m.label(f"{date_key}", "title-2"))
            
            for event in date_events:
                recurring_text = f"[{event.recurring}]" if event.recurring else ""

                source_text = f"[{event.source.replace('/', ' > ')}]"
                fields.append(m.labelline(
                    [event.description, recurring_text, source_text], ["", "small inactive", "small inactive"]))

            fields.append(m.space(1))
    
    return [m.form("overview", "overview", fields, open=True)]
