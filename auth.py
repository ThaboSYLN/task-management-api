from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# ========================================
# CONFIGURATION
# ========================================
SECRET_KEY = "your-secret-key-change-in-production-123456789"  # Change this in real apps!
ALGORITHM = "HS256"  # Encryption algorithm for JWT
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Tokens expire after 30 minutes

# ========================================
# PASSWORD HASHING SETUP
# ========================================
# This handles password hashing securely
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# This tells FastAPI to expect "Bearer token" in Authorization header
security = HTTPBearer()

# ========================================
# PYDANTIC MODELS FOR AUTH
# ========================================
class UserLogin(BaseModel):
    """What we expect when user tries to login"""
    username: str
    password: str

class UserCreate(BaseModel):
    """What we expect when user registers"""
    username: str
    password: str

class Token(BaseModel):
    """What we return after successful login"""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Data we extract from JWT token"""
    username: Optional[str] = None

# ========================================
# SIMPLE USER DATABASE
# ========================================
# In a real app, this would be in your SQLite/PostgreSQL database
# For now, we'll use a dictionary to keep it simple
fake_users_db = {
    "testuser": {
        "username": "testuser",
        # This is the hashed version of password "secret"
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
    }
}

# ========================================
# PASSWORD FUNCTIONS
# ========================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check if a plain password matches the hashed version
    
    Args:
        plain_password: The password user typed
        hashed_password: The stored hashed password
    
    Returns:
        True if passwords match, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hash a plain password for safe storage
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)

# ========================================
# USER MANAGEMENT FUNCTIONS
# ========================================
def get_user(username: str):
    """
    Get user from our 'database'
    
    Args:
        username: Username to look for
    
    Returns:
        User dict if found, None otherwise
    """
    if username in fake_users_db:
        return fake_users_db[username]
    return None

def authenticate_user(username: str, password: str):
    """
    Verify user credentials
    
    Args:
        username: Username
        password: Plain text password
    
    Returns:
        User dict if credentials are valid, False otherwise
    """
    user = get_user(username)
    if not user:
        return False  # User doesn't exist
    
    if not verify_password(password, user["hashed_password"]):
        return False  # Wrong password
    
    return user  # Success!

def create_user(username: str, password: str) -> dict:
    """
    Create a new user
    
    Args:
        username: Desired username
        password: Plain text password
    
    Returns:
        Success message dict
    
    Raises:
        HTTPException if username already exists
    """
    if username in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Hash the password before storing
    hashed_password = get_password_hash(password)
    fake_users_db[username] = {
        "username": username,
        "hashed_password": hashed_password
    }
    
    return {"username": username, "message": "User created successfully"}

# ========================================
# JWT TOKEN FUNCTIONS
# ========================================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a JWT access token
    
    Args:
        data: Data to encode in the token (usually username)
        expires_delta: How long token should be valid
    
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    # Add expiration to token data
    to_encode.update({"exp": expire})
    
    # Create and return the JWT token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ========================================
# DEPENDENCY FOR PROTECTED ROUTES
# ========================================
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Dependency function that extracts and validates JWT token from request
    
    This function will be used with FastAPI's Depends() to protect routes.
    It automatically:
    1. Extracts the token from Authorization header
    2. Verifies the token is valid
    3. Returns the user information
    
    Args:
        credentials: Automatically injected by FastAPI from Authorization header
    
    Returns:
        User dict if token is valid
    
    Raises:
        HTTPException if token is invalid/expired/missing
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Extract the actual token from credentials
        token = credentials.credentials
        
        # Decode and verify the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extract username from token
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
            
        token_data = TokenData(username=username)
        
    except JWTError:
        # Token is invalid/expired/malformed
        raise credentials_exception
    
    # Get user from database
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    
    return user