"""
Display helpers for protest details, shared by any chat format.
"""

from datetime import datetime


def fmt_date(value: str) -> str:
    # Normalize a date string like "Feb 2, 2024" to mm/dd/yyyy
    try:
        return datetime.strptime(value, "%b %d, %Y").strftime("%m/%d/%Y")
    except (ValueError, TypeError):
        return value
