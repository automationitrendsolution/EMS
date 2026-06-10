from django import template

register = template.Library()


@register.filter
def humanize_enum(value):
    """Turn an enum value like 'in_progress' / 'on_hold' into a human label
    ('In Progress' / 'On Hold'). Safe for single words too ('low' -> 'Low')."""
    if value is None:
        return ""
    return str(value).replace("_", " ").title()


@register.filter
def hours_to_hms(value):
    """Convert a float hours value (e.g. 1.5) to HH:MM:SS string (01:30:00)."""
    try:
        total_secs = int(float(value) * 3600)
    except (TypeError, ValueError):
        return "00:00:00"
    negative = total_secs < 0
    total_secs = abs(total_secs)
    h = total_secs // 3600
    m = (total_secs % 3600) // 60
    s = total_secs % 60
    result = f"{h:02d}:{m:02d}:{s:02d}"
    return f"-{result}" if negative else result


@register.filter
def secs_to_hms(value):
    """Convert integer seconds to HH:MM:SS string."""
    try:
        total_secs = int(value)
    except (TypeError, ValueError):
        return "00:00:00"
    negative = total_secs < 0
    total_secs = abs(total_secs)
    h = total_secs // 3600
    m = (total_secs % 3600) // 60
    s = total_secs % 60
    result = f"{h:02d}:{m:02d}:{s:02d}"
    return f"-{result}" if negative else result
