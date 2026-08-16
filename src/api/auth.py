"""
Authentication and authorization utilities for API endpoints.
"""

from fastapi import Depends, HTTPException, Header
from typing import Optional
from src.auth.utils import login, ROLES
from src.utils.logger import setup_logger
from src.utils.exceptions import AuthenticationException

logger = setup_logger(__name__)

# Simple token storage (in-memory for now, can be replaced with proper JWT)
# In production, use proper JWT tokens with expiration
_active_tokens: dict[str, dict] = {}


def create_token(user_data: dict) -> str:
    """
    Create a simple token for a user (replace with JWT in production).
    
    Args:
        user_data: Dict with 'id', 'email', 'role'
        
    Returns:
        Token string
    """
    import secrets
    token = secrets.token_urlsafe(32)
    _active_tokens[token] = user_data
    logger.debug(f"Token created for user: {user_data['email']}")
    return token


def verify_token(token: str) -> dict:
    """
    Verify a token and return user data.
    
    Args:
        token: Token string
        
    Returns:
        User data dict
        
    Raises:
        AuthenticationException: If token is invalid
    """
    if token not in _active_tokens:
        raise AuthenticationException("Invalid or expired token")
    return _active_tokens[token]


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Dependency to extract and verify current user from Authorization header.
    
    Expected header format: "Bearer <token>"
    
    Raises:
        HTTPException: 401 if authentication fails
    """
    if not authorization:
        logger.warning("Request without Authorization header")
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    try:
        scheme, token = authorization.split(" ")
        if scheme.lower() != "bearer":
            raise ValueError("Invalid auth scheme")
        
        user_data = verify_token(token)
        return user_data
    except (ValueError, AuthenticationException) as e:
        logger.warning(f"Authentication failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")


def require_role(required_role: str):
    """
    Dependency factory to check user has required role.
    
    Usage:
        @router.get("/admin-only")
        def admin_endpoint(user = Depends(require_role("admin"))):
            pass
    """
    def check_role(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") != required_role and user.get("role") != "super_admin":
            logger.warning(f"Unauthorized access attempt by {user.get('email')}: required {required_role}, has {user.get('role')}")
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return check_role


def require_any_role(*roles: str):
    """
    Dependency factory to check user has any of the required roles.
    """
    def check_roles(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            logger.warning(f"Unauthorized access attempt by {user.get('email')}: required one of {roles}, has {user.get('role')}")
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return check_roles


class Optional_Auth:
    """
    Optional authentication - returns user data if authenticated, None otherwise.
    """
    def __call__(self, authorization: Optional[str] = Header(None)) -> Optional[dict]:
        if not authorization:
            return None
        
        try:
            scheme, token = authorization.split(" ")
            if scheme.lower() != "bearer":
                return None
            return verify_token(token)
        except Exception:
            return None


optional_auth = Optional_Auth()
