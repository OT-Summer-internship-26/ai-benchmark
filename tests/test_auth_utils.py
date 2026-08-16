"""
Unit tests for authentication utilities.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.auth.utils import (
    hash_password,
    verify_password,
    login,
    create_user,
    ROLES,
)


class TestPasswordHashing:
    """Test password hashing and verification."""
    
    def test_hash_password_creates_hash(self):
        """Test that hash_password returns a non-empty hash."""
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert "$2b$" in hashed  # bcrypt hash prefix
    
    def test_verify_password_success(self):
        """Test verifying a correct password."""
        password = "correct_password"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_failure(self):
        """Test verifying an incorrect password."""
        password = "correct_password"
        hashed = hash_password(password)
        
        assert verify_password("wrong_password", hashed) is False
    
    def test_hash_consistency(self):
        """Test that same password produces different hashes (salt)."""
        password = "test_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2  # Different due to salt
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestLogin:
    """Test login functionality."""
    
    @patch('src.auth.utils.SessionLocal')
    def test_login_success(self, mock_session_local):
        """Test successful login."""
        # Setup
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        test_user = Mock()
        test_user.id = 1
        test_user.email = "user@example.com"
        test_user.mot_de_passe_hash = hash_password("correct_password")
        test_user.role = "client"
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = test_user
        
        # Execute
        user, error = login("user@example.com", "correct_password")
        
        # Verify
        assert error is None
        assert user is not None
        assert user["id"] == 1
        assert user["email"] == "user@example.com"
        assert user["role"] == "client"
        mock_db.close.assert_called_once()
    
    @patch('src.auth.utils.SessionLocal')
    def test_login_wrong_password(self, mock_session_local):
        """Test login with wrong password."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        test_user = Mock()
        test_user.mot_de_passe_hash = hash_password("correct_password")
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = test_user
        
        user, error = login("user@example.com", "wrong_password")
        
        assert user is None
        assert error is not None
        assert "Mot de passe" in error or "password" in error.lower()
    
    @patch('src.auth.utils.SessionLocal')
    def test_login_non_existent_user(self, mock_session_local):
        """Test login with non-existent user."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None
        
        user, error = login("nonexistent@example.com", "password")
        
        assert user is None
        assert error is not None
    
    def test_login_empty_credentials(self):
        """Test login with empty credentials."""
        user, error = login("", "")
        assert user is None
        assert error is not None
    
    def test_login_invalid_email(self):
        """Test login with invalid email format."""
        user, error = login("not_an_email", "password")
        assert user is None
        assert error is not None


class TestCreateUser:
    """Test user creation."""
    
    @patch('src.auth.utils.SessionLocal')
    def test_create_user_success(self, mock_session_local):
        """Test successful user creation."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        # Setup: no existing user
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None
        
        success, message = create_user("newuser@example.com", "secure_password", "client")
        
        assert success is True
        assert "créé" in message.lower() or "created" in message.lower()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()
    
    @patch('src.auth.utils.SessionLocal')
    def test_create_user_already_exists(self, mock_session_local):
        """Test creating user that already exists."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        # Setup: user already exists
        existing_user = Mock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = existing_user
        
        success, message = create_user("existing@example.com", "password", "client")
        
        assert success is False
        assert "existe" in message.lower() or "already" in message.lower()
    
    def test_create_user_invalid_email(self):
        """Test creating user with invalid email."""
        success, message = create_user("invalid_email", "password", "client")
        assert success is False
        # Message can be in French or English, check for either
        assert "email" in message.lower() or "e-mail" in message.lower()
    
    def test_create_user_weak_password(self):
        """Test creating user with weak password."""
        success, message = create_user("user@example.com", "short", "client")
        assert success is False
        assert "6" in message  # Should mention minimum length
    
    def test_create_user_invalid_role(self):
        """Test creating user with invalid role."""
        success, message = create_user("user@example.com", "secure_password", "invalid_role")
        assert success is False
        assert "rôle" in message.lower() or "role" in message.lower()
    
    def test_create_user_empty_credentials(self):
        """Test creating user with empty credentials."""
        success, message = create_user("", "", "client")
        assert success is False
        
        success, message = create_user("user@example.com", "", "client")
        assert success is False
    
    @patch('src.auth.utils.SessionLocal')
    def test_create_user_integrity_error(self, mock_session_local):
        """Test handling of race condition (IntegrityError)."""
        from sqlalchemy.exc import IntegrityError
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        # Setup: no existing user first check, but IntegrityError on commit
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None
        
        mock_db.commit.side_effect = IntegrityError("Unique constraint failed", None, None)
        
        success, message = create_user("user@example.com", "secure_password", "client")
        
        assert success is False
        assert "existe" in message.lower() or "already" in message.lower()
        mock_db.rollback.assert_called_once()


class TestRoles:
    """Test ROLES constant."""
    
    def test_roles_defined(self):
        """Test that ROLES constant is defined."""
        assert ROLES is not None
        assert isinstance(ROLES, tuple)
        assert len(ROLES) > 0
    
    def test_roles_values(self):
        """Test expected role values."""
        assert "client" in ROLES
        assert "admin" in ROLES
        assert "super_admin" in ROLES
