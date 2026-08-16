"""
Authentication routes for user login and token management.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from src.auth.utils import login, create_user, ROLES
from src.api.auth import create_token, get_current_user
from src.utils.logger import setup_logger
from src.utils.validation import validate_email, validate_password

logger = setup_logger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    """Login request body."""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")


class LoginResponse(BaseModel):
    """Login response body."""
    token: str
    user: dict


class CreateUserRequest(BaseModel):
    """Create user request body."""
    email: str = Field(..., description="User email")
    password: str = Field(..., min_length=6, description="User password (minimum 6 chars)")
    role: str = Field(default="client", description="User role")


class CreateUserResponse(BaseModel):
    """Create user response body."""
    success: bool
    message: str


class CurrentUserResponse(BaseModel):
    """Current user info response."""
    id: int
    email: str
    role: str


@router.post("/login", response_model=LoginResponse)
def login_endpoint(request: LoginRequest):
    """
    Authenticate user with email and password.
    
    Returns a token that can be used in subsequent requests via
    the Authorization: Bearer <token> header.
    """
    try:
        # Validate input
        if not request.email or not request.password:
            logger.warning("Login attempt with empty credentials")
            raise HTTPException(status_code=400, detail="Email and password are required")
        
        if not validate_email(request.email):
            logger.warning(f"Login attempt with invalid email format: {request.email}")
            raise HTTPException(status_code=400, detail="Invalid email format")
        
        # Authenticate
        user, error = login(request.email, request.password)
        
        if error:
            logger.warning(f"Failed login for {request.email}: {error}")
            # Don't reveal whether email exists or password is wrong (security)
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Create token
        token = create_token(user)
        logger.info(f"User logged in: {request.email}")
        
        return LoginResponse(token=token, user=user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.post("/register", response_model=CreateUserResponse)
def register_endpoint(request: CreateUserRequest):
    """
    Register a new user account.
    
    Validates email, password strength, and role.
    """
    try:
        # Validate input
        if not validate_email(request.email):
            logger.warning(f"Registration attempt with invalid email: {request.email}")
            raise HTTPException(status_code=400, detail="Invalid email format")
        
        is_valid, pwd_error = validate_password(request.password)
        if not is_valid:
            logger.warning(f"Registration attempt with weak password for {request.email}")
            raise HTTPException(status_code=400, detail=pwd_error)
        
        if request.role not in ROLES:
            logger.warning(f"Registration attempt with invalid role: {request.role}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Allowed roles: {', '.join(ROLES)}"
            )
        
        # Create user
        success, message = create_user(request.email, request.password, request.role)
        
        if not success:
            logger.warning(f"Failed registration for {request.email}: {message}")
            raise HTTPException(status_code=400, detail=message)
        
        logger.info(f"New user registered: {request.email} (role: {request.role})")
        return CreateUserResponse(success=True, message=message)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}")
        raise HTTPException(status_code=500, detail="Registration failed")


@router.get("/me", response_model=CurrentUserResponse)
def get_current_user_endpoint(user: dict = Depends(get_current_user)):
    """
    Get information about the currently authenticated user.
    
    Requires: Authorization: Bearer <token> header
    """
    return CurrentUserResponse(
        id=user["id"],
        email=user["email"],
        role=user["role"]
    )
