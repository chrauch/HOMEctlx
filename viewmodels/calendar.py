# This file is part of HOMEctlx. Copyright (C) 2024 Christian Rauch.
# Distributed under terms of the GPL3 license.

"""
View-model for calendar events.
"""

from datetime import datetime, timedelta

from flask import session
import services.calmgr as cm
import services.meta as m
import services.state as state


def ctl() -> list[m.view]:
    """Starting point."""
    return [m.view("_body", "calendar", [agenda(), calendar_view(), add_event(), edit_events()])]


def navigate_calendar(direction: str) -> m.view:
    """
    Navigate to previous or next months.
    
    Args:
        direction: 'next' or 'previous'
    """
    # Get current offset from state, default to 0
    current_offset = int(state.get('calendar.overview.month_offset', 0))
    
    if direction == 'next':
        state.set('calendar.overview.month_offset', current_offset + 1)
    elif direction == 'previous':
        state.set('calendar.overview.month_offset', current_offset - 1)
    
    return calendar_view()


def calendar_view() -> m.form:
    """
    Display calendar grid for current and next month.
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get month offset from state (default 0 = current month)
    month_offset = int(state.get('calendar.overview.month_offset', 0))
    
    # Calculate base month with offset
    base_month_start = today.replace(day=1)
    for _ in range(abs(month_offset)):
        if month_offset > 0:
            base_month_start = (base_month_start + timedelta(days=32)).replace(day=1)
        else:
            base_month_start = (base_month_start - timedelta(days=1)).replace(day=1)
    
    # Generate two consecutive months
    first_month_start = base_month_start
    second_month_start = (first_month_start + timedelta(days=32)).replace(day=1)
    
    # Navigation buttons
    nav_prev = m.execute_params("calendar/navigate_calendar", "previous month", {"direction": "previous"}, style="small")
    nav_next = m.execute_params("calendar/navigate_calendar", "next month", {"direction": "next"}, style="small")
    nav_fields = m.table(rows=[[nav_prev, m.label(" "), nav_next]])
    
    # Generate both month tables
    first_month_table = generate_month_table(first_month_start, today)
    second_month_table = generate_month_table(second_month_start, today)
    
    # Calendar grid form
    fields = [
        nav_fields,
        m.space(1),
        m.label(first_month_start.strftime("%B %Y"), "title-2"),
        first_month_table,
        m.space(1),
        m.label(second_month_start.strftime("%B %Y"), "title-2"),
        second_month_table
    ]
    
    return m.form("calendar_grid", "overview", fields, open=True)


def generate_month_table(month_start: datetime, today: datetime) -> m.table:
    """
    Generate a calendar grid table for a specific month.
    """
    import calendar
    
    # Get month info
    year = month_start.year
    month = month_start.month
    
    # Get events for this month
    month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    events = cm.get_events(month_start, month_end)
    
    # Group events by date
    events_by_date = {}
    for event in events:
        date_key = event.date.strftime('%Y-%m-%d')
        if date_key not in events_by_date:
            events_by_date[date_key] = []
        events_by_date[date_key].append(event)
    
    # Build calendar grid
    cal = calendar.monthcalendar(year, month)
    headers = ['Week', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    rows = []
    for week in cal:
        row = []
        
        # Add week number as first column
        # Get the first valid day of this week to calculate week number
        first_valid_day = next((d for d in week if d != 0), None)
        if first_valid_day:
            week_date = datetime(year, month, first_valid_day)
            week_number = week_date.isocalendar()[1]
            row.append(m.label("# " + str(week_number), 'small inactive glow-a'))
        else:
            row.append(m.space(1))
        
        for day in week:
            if day == 0:
                # Empty cell for days outside the month
                row.append(m.space(1))
            else:
                # Create date for this day
                day_date = datetime(year, month, day)
                date_key = day_date.strftime('%Y-%m-%d')
                
                # Check if there are events on this day
                day_events = events_by_date.get(date_key, [])
                
                # Style based on day type
                style = 'small '
                if day_date == today:
                    style += 'glow-a'
                elif day_date < today:
                    style += 'inactive'
                
                # Build cell content
                if day_events:
                    # Day with events - create section with day number and event labels
                    content = []
                    # Add day number
                    content.append(m.label(str(day), style))
                    # Add each event as separate label
                    for event in day_events:
                        desc = event.description
                        # Replace newlines with backslash for single-line display
                        display_text = desc.replace('\n', ' \\ ')
                        # Truncate if too long, use full description as details
                        if len(display_text) > 18:
                            display_text = display_text[:15] + "..."
                        content.append(m.label(display_text, 'small info', details=str(event)))
                    row.append(m.section(content))
                else:
                    # Day without events - simple label
                    row.append(m.label(str(day), style))
        rows.append(row)
    
    # Create and return table
    return m.table(rows, headers=headers, style='calendar-grid')


def add_event() -> m.form:
    """
    Add a new event to calendar.
    """
    # Get calendar files for dropdown
    calendar_files = cm.get_calendar_files()
    
    # Build choices for calendar file selection
    file_choices = []
    
    # Add user calendar files
    for file_path in calendar_files['user']:
        display_name =  session['uname'] + " > " + file_path[-1].replace('.calx', '')
        file_value = '/'.join(file_path)
        file_choices.append(m.choice(file_value, display_name))
    
    # Add global calendar files
    for file_path in calendar_files['global']:
        display_name = "global > " + file_path[-1].replace('.calx', '')
        file_value = '/'.join(file_path)  # e.g., "calendar/global/holidays.calx"
        file_choices.append(m.choice(file_value, display_name))
    
    # Load saved values from state
    saved_date = state.get('calendar.add.date')
    if not saved_date:
        saved_date = datetime.now().strftime('%Y-%m-%d')
    
    saved_event_type = 'once'
    saved_end_date = ''
    
    saved_calendar_file = state.get('calendar.add.calendar_file')
    
    saved_keep_sorted = state.get('calendar.add.keep_sorted', True)
    
    # Verify saved calendar file still exists
    all_file_values = ['/'.join(fp) for fp in calendar_files['user']] + ['/'.join(fp) for fp in calendar_files['global']]
    if saved_calendar_file and saved_calendar_file not in all_file_values:
        saved_calendar_file = None
    
    if not saved_calendar_file:
        # Default to first user file or first global file
        if calendar_files['user']:
            saved_calendar_file = '/'.join(calendar_files['user'][0])
        elif calendar_files['global']:
            saved_calendar_file = '/'.join(calendar_files['global'][0])
    
    # Event type choices
    event_type_choices = [
        m.choice('once', 'Once'),
        m.choice('daily', 'Daily'),
        m.choice('weekly', 'Weekly'),
        m.choice('monthly', 'Monthly'),
        m.choice('yearly', 'Yearly')
    ]
    
    # Keep sorted choices
    keep_sorted_choices = [
        m.choice('true', 'Yes'),
        m.choice('false', 'No')
    ]
    
    # Find the matching choice object for the saved event type
    saved_event_type_choice = next((c for c in event_type_choices if c.value == saved_event_type), event_type_choices[0])
    
    # Find the matching choice object for the saved calendar file
    saved_calendar_file_choice = next((c for c in file_choices if c.value == saved_calendar_file), file_choices[0] if file_choices else None)
    
    # Find the matching choice object for keep_sorted
    saved_keep_sorted_value = 'true' if saved_keep_sorted else 'false'
    saved_keep_sorted_choice = next((c for c in keep_sorted_choices if c.value == saved_keep_sorted_value), keep_sorted_choices[0])
    
    # Create form with table layout
    table_rows = [
        [m.label("Date"), m.text("date", saved_date, "YYYY-MM-DD")],
        [m.label("Description"), m.text_big("description", "", "event description")],
        [m.label("Recurrence interval"), m.select("event_type", event_type_choices, saved_event_type_choice, "recurrence")],
        [m.label("Recurrence end date"), m.text("end_date", saved_end_date, "YYYY-MM-DD (optional, for recurring)")],
        [m.label("Calendar"), m.select("calendar_file", file_choices, saved_calendar_file_choice, "target file") if file_choices else m.label("No calendar files", "info")],
        [m.label("Keep sorted"), m.select("keep_sorted", keep_sorted_choices, saved_keep_sorted_choice, "sort and clean file")]
    ]
    
    fields = [
        m.table(rows=table_rows),
        m.execute("calendar/save_event", "add event")
    ]
    
    if not file_choices:
        fields.insert(0, m.label("Create a .calx file in calendar/global/ or your user calendar directory first", "info"))
    
    return m.form("add_event", "add", fields, open=False)


def save_event(date: str, event_type: str, description: str, calendar_file: str, keep_sorted: str, end_date: str = '') -> list[m.view]:
    """
    Save a new event to the specified calendar file.
    """
    # Convert keep_sorted string to boolean
    keep_sorted_bool = (keep_sorted == 'true')
    
    # Save form values to state (except description which resets)
    state.set('calendar.add.date', date)
    state.set('calendar.add.event_type', event_type)
    state.set('calendar.add.calendar_file', calendar_file)
    state.set('calendar.add.keep_sorted', keep_sorted_bool)
    state.set('calendar.add.end_date', end_date)
    
    # Parse the file path
    file_path_parts = calendar_file.split('/')
    
    try:
        # Use the calendar manager service to add the event
        cm.add_event_to_file(date, event_type, description, file_path_parts, keep_sorted_bool, end_date)
        return ctl()
    except ValueError as e:
        return [m.error(str(e))]
    except Exception as e:
        return [m.error(f"Failed to save event: {str(e)}")]


def edit_events() -> m.form:
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
    
    return m.form("edit_events", "edit", fields, open=False)


def agenda(start_date: str = None, end_date: str = None, open: bool = False) -> m.form:
    """
    Display overview of events in a date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format (default: today)
        end_date: End date in YYYY-MM-DD format (default: from saved range or 14 days)
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
        # Use saved range or default to 14 days
        saved_range = int(state.get('calendar.upcoming.days_range', 14))
        end = start + timedelta(days=saved_range)
    
    # Calculate and save the days range
    days_range = (end - start).days
    state.set('calendar.upcoming.days_range', days_range)
    
    # Get events
    events = cm.get_events(start, end)
    
    # Date range controls
    default_start = start.strftime("%Y-%m-%d")
    default_end = end.strftime("%Y-%m-%d")
    
    controls = [
        m.text("start_date", default_start, "from"),
        m.text("end_date", default_end, "to"),
        m.execute_params("calendar/agenda", "refresh", { "open": True })
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
                recurring_text = ""
                if event.recurring:
                    recurring_text = f"[{event.recurring}"
                    if event.end_date:
                        recurring_text += f",end:{event.end_date.strftime('%Y-%m-%d')}"
                    recurring_text += "] "
                source_text = f"[{event.source.replace('/', ' > ')}]"
                
                event_table = m.table(rows=[
                    [m.label(event.description, "")],
                    [m.label(recurring_text + source_text, "small inactive")]
                ])
                fields.append(event_table)

            fields.append(m.space(1))
    
    return m.form("agenda", "upcoming", fields, open=open)
