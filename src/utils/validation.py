"""
Input validation and sanitization utilities.
"""

import re
from typing import Any, List, Optional


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email.strip()) is not None


def validate_password(password: str, min_length: int = 6) -> tuple[bool, Optional[str]]:
    """
    Validate password strength.
    
    Returns:
        (is_valid, error_message)
    """
    if not password:
        return False, "Password is required."
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters."
    return True, None


def validate_department(department: str, allowed: List[str]) -> bool:
    """Validate department is in allowed list."""
    return department.strip() in allowed


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize string input by stripping whitespace and truncating.
    
    Args:
        value: Input string
        max_length: Maximum allowed length
    
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return ""
    sanitized = value.strip()
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    return sanitized


def validate_positive_int(value: Any, name: str = "value") -> tuple[bool, Optional[str], int]:
    """
    Validate that value is a positive integer.
    
    Returns:
        (is_valid, error_message, parsed_value)
    """
    try:
        parsed = int(value)
        if parsed <= 0:
            return False, f"{name} must be positive", 0
        return True, None, parsed
    except (ValueError, TypeError):
        return False, f"{name} must be a valid integer", 0


def validate_float_range(value: Any, min_val: float = 0.0, max_val: float = 1.0) -> tuple[bool, Optional[str], float]:
    """
    Validate that value is a float within range.
    
    Returns:
        (is_valid, error_message, parsed_value)
    """
    try:
        parsed = float(value)
        if not (min_val <= parsed <= max_val):
            return False, f"Value must be between {min_val} and {max_val}", 0.0
        return True, None, parsed
    except (ValueError, TypeError):
        return False, "Value must be a valid number", 0.0


def validate_list_not_empty(lst: Any) -> tuple[bool, Optional[str]]:
    """Validate that list is not empty."""
    if not isinstance(lst, list) or len(lst) == 0:
        return False, "List cannot be empty"
    return True, None
