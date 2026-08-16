"""
Unit tests for utility functions (validation, retry, exceptions).
"""

import pytest
from src.utils.validation import (
    validate_email,
    validate_password,
    validate_positive_int,
    validate_float_range,
    validate_list_not_empty,
    sanitize_string,
)


class TestEmailValidation:
    """Test email validation."""
    
    def test_valid_email(self):
        assert validate_email("user@example.com") is True
        assert validate_email("test.user+tag@sub.example.co.uk") is True
    
    def test_invalid_email(self):
        assert validate_email("invalid") is False
        assert validate_email("@example.com") is False
        assert validate_email("user@") is False
        assert validate_email("") is False
    
    def test_email_with_whitespace(self):
        assert validate_email("  user@example.com  ") is True


class TestPasswordValidation:
    """Test password validation."""
    
    def test_valid_password(self):
        is_valid, error = validate_password("secure_password123")
        assert is_valid is True
        assert error is None
    
    def test_short_password(self):
        is_valid, error = validate_password("short")
        assert is_valid is False
        assert error is not None
        assert "6 characters" in error
    
    def test_empty_password(self):
        is_valid, error = validate_password("")
        assert is_valid is False


class TestPositiveIntValidation:
    """Test positive integer validation."""
    
    def test_valid_positive_int(self):
        is_valid, error, value = validate_positive_int(42, "test_value")
        assert is_valid is True
        assert error is None
        assert value == 42
    
    def test_zero(self):
        is_valid, error, value = validate_positive_int(0, "test_value")
        assert is_valid is False
        assert error is not None
    
    def test_negative(self):
        is_valid, error, value = validate_positive_int(-5, "test_value")
        assert is_valid is False
    
    def test_non_integer(self):
        is_valid, error, value = validate_positive_int("not_an_int", "test_value")
        assert is_valid is False
        assert error is not None


class TestFloatRangeValidation:
    """Test float range validation."""
    
    def test_valid_float_in_range(self):
        is_valid, error, value = validate_float_range(0.5, 0.0, 1.0)
        assert is_valid is True
        assert error is None
        assert value == 0.5
    
    def test_float_below_range(self):
        is_valid, error, value = validate_float_range(-0.1, 0.0, 1.0)
        assert is_valid is False
        assert error is not None
    
    def test_float_above_range(self):
        is_valid, error, value = validate_float_range(1.5, 0.0, 1.0)
        assert is_valid is False
    
    def test_boundaries(self):
        # Test min boundary
        is_valid, error, value = validate_float_range(0.0, 0.0, 1.0)
        assert is_valid is True
        
        # Test max boundary
        is_valid, error, value = validate_float_range(1.0, 0.0, 1.0)
        assert is_valid is True


class TestListValidation:
    """Test list validation."""
    
    def test_valid_list(self):
        is_valid, error = validate_list_not_empty([1, 2, 3])
        assert is_valid is True
        assert error is None
    
    def test_empty_list(self):
        is_valid, error = validate_list_not_empty([])
        assert is_valid is False
        assert error is not None
    
    def test_not_a_list(self):
        is_valid, error = validate_list_not_empty("not_a_list")
        assert is_valid is False
        assert error is not None


class TestStringSanitization:
    """Test string sanitization."""
    
    def test_basic_sanitization(self):
        assert sanitize_string("  hello  ") == "hello"
        assert sanitize_string("test") == "test"
    
    def test_string_truncation(self):
        long_string = "a" * 1000
        result = sanitize_string(long_string, max_length=100)
        assert len(result) == 100
    
    def test_empty_string(self):
        assert sanitize_string("") == ""
    
    def test_non_string_input(self):
        assert sanitize_string(None, 100) == ""
        assert sanitize_string(123, 100) == ""
