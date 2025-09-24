import time
import secrets
from typing import Dict, Optional
from datetime import datetime, timedelta

import jwt
from dotenv import dotenv_values
from passlib.context import CryptContext
from app.config.database import refresh_tokens_collection

JWT_SECRET = dotenv_values(".env")['SECRET']
JWT_ALGORITHM = dotenv_values(".env")['ALGORITHM']

# Token expiry times (in seconds)
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # 15 minutes
REFRESH_TOKEN_EXPIRE_DAYS = 7     # 7 days

# create a password context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a plain-text password."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)

def token_response(access_token: str, refresh_token: str, token_type: str = "bearer"):
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": token_type
    }

def generate_access_token(user_id: str) -> str:
    """Generate a short-lived access token"""
    payload = {
        "user_id": user_id,
        "token_type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def generate_refresh_token(user_id: str) -> str:
    """Generate a long-lived refresh token"""
    payload = {
        "user_id": user_id,
        "token_type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.utcnow(),
        "jti": secrets.token_urlsafe(32)  # Unique identifier for token revocation
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def sign_jwt(user_id: str) -> Dict[str, str]:
    """Generate both access and refresh tokens"""
    access_token = generate_access_token(user_id)
    refresh_token = generate_refresh_token(user_id)
    
    # Store refresh token in database for tracking
    refresh_payload = decode_jwt(refresh_token)
    if refresh_payload:
        store_refresh_token(
            user_id,
            refresh_payload.get("jti"),
            datetime.utcfromtimestamp(refresh_payload.get("exp"))
        )
    
    return token_response(access_token, refresh_token)

def decode_jwt(token: str) -> Optional[dict]:
    """Decode and validate JWT token"""
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded_token
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def verify_access_token(token: str) -> Optional[dict]:
    """Verify access token specifically"""
    payload = decode_jwt(token)
    if payload and payload.get("token_type") == "access":
        return payload
    return None

def verify_refresh_token(token: str) -> Optional[dict]:
    """Verify refresh token specifically"""
    payload = decode_jwt(token)
    if payload and payload.get("token_type") == "refresh":
        return payload
    return None

def store_refresh_token(user_id: str, token_jti: str, expires_at: datetime) -> bool:
    """Store refresh token information in database"""
    try:
        refresh_tokens_collection.insert_one({
            "user_id": user_id,
            "token_jti": token_jti,
            "expires_at": expires_at,
            "created_at": datetime.utcnow(),
            "is_revoked": False
        })
        return True
    except Exception:
        return False

def is_refresh_token_valid(token_jti: str) -> bool:
    """Check if refresh token is valid and not revoked"""
    token_doc = refresh_tokens_collection.find_one({
        "token_jti": token_jti,
        "is_revoked": False,
        "expires_at": {"$gt": datetime.utcnow()}
    })
    return token_doc is not None

def revoke_refresh_token(token_jti: str) -> bool:
    """Revoke a refresh token"""
    try:
        result = refresh_tokens_collection.update_one(
            {"token_jti": token_jti},
            {"$set": {"is_revoked": True, "revoked_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
    except Exception:
        return False

def revoke_all_user_refresh_tokens(user_id: str) -> bool:
    """Revoke all refresh tokens for a user"""
    try:
        refresh_tokens_collection.update_many(
            {"user_id": user_id, "is_revoked": False},
            {"$set": {"is_revoked": True, "revoked_at": datetime.utcnow()}}
        )
        return True
    except Exception:
        return False

def refresh_access_token(refresh_token: str) -> Optional[Dict[str, str]]:
    """Generate new access token from valid refresh token"""
    payload = verify_refresh_token(refresh_token)
    if not payload:
        return None
    
    user_id = payload.get("user_id")
    token_jti = payload.get("jti")
    
    if not user_id or not token_jti:
        return None
    
    # Check if refresh token is still valid in database
    if not is_refresh_token_valid(token_jti):
        return None
    
    # Generate new access token
    new_access_token = generate_access_token(user_id)
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }
