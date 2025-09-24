from fastapi import APIRouter, Body, HTTPException, status, Response, Request
import datetime

from app.auth.auth_handler import (
    sign_jwt, hash_password, verify_password, 
    refresh_access_token, revoke_refresh_token,
    revoke_all_user_refresh_tokens, verify_refresh_token
)
from app.models.user import (
    UserSchema, UserLoginSchema, RefreshTokenSchema,
    TokenResponseSchema, AccessTokenResponseSchema
)
from app.config.database import users_collection

auth_root = APIRouter(prefix="/user", tags=["user"])

@auth_root.post("/signup")
async def create_user(user: UserSchema = Body(...), response: Response = None):
    try:
        res = users_collection.find_one({"email": user.email})
        if res:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )
        
        hashed_password = hash_password(user.password)
        
        user_data = {
            **user.model_dump(),
            "password": hashed_password,
            "created_at": datetime.datetime.now(),
            "updated_at": datetime.datetime.now()
        }
        
        res = users_collection.insert_one(user_data)
        
        if not res.acknowledged:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        # Generate tokens
        tokens = sign_jwt(str(res.inserted_id))
        
        # Set HTTP-only cookies
        response.set_cookie(
            key="access_token",
            value=tokens["access_token"],
            max_age=15 * 60,  # 15 minutes
            httponly=True,
            secure=True,  # Set to True in production with HTTPS
            samesite="lax"
        )
        
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            max_age=7 * 24 * 60 * 60,  # 7 days
            httponly=True,
            secure=True,  # Set to True in production with HTTPS
            samesite="lax"
        )
        
        return {"message": "User created successfully", "user_id": str(res.inserted_id)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    
@auth_root.post("/login")
async def user_login(user: UserLoginSchema = Body(...), response: Response = None):
    try:
        db_user = users_collection.find_one({"email": user.email})
        
        # Check if user exists and password is correct
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not verify_password(user.password, db_user["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Generate tokens
        tokens = sign_jwt(db_user["_id"].__str__())
        
        # Set HTTP-only cookies
        response.set_cookie(
            key="access_token",
            value=tokens["access_token"],
            max_age=15 * 60,  # 15 minutes
            httponly=True,
            secure=True,  # Set to True in production with HTTPS
            samesite="lax"
        )
        
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            max_age=7 * 24 * 60 * 60,  # 7 days
            httponly=True,
            secure=True,  # Set to True in production with HTTPS
            samesite="lax"
        )
        
        return {"message": "Login successful", "user_id": db_user["_id"].__str__()}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@auth_root.post("/refresh")
async def refresh_token(request: Request, response: Response):
    """Refresh access token using refresh token from cookies"""
    try:
        # Get refresh token from cookies
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No refresh token provided"
            )
        
        new_tokens = refresh_access_token(refresh_token)
        if not new_tokens:
            # Clear invalid cookies
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # Set new access token cookie
        response.set_cookie(
            key="access_token",
            value=new_tokens["access_token"],
            max_age=15 * 60,  # 15 minutes
            httponly=True,
            secure=True,  # Set to True in production with HTTPS
            samesite="lax"
        )
        
        return {"message": "Access token refreshed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@auth_root.post("/logout")
async def logout(request: Request, response: Response):
    """Logout user by revoking refresh token and clearing cookies"""
    try:
        # Get refresh token from cookies
        refresh_token = request.cookies.get("refresh_token")
        
        if refresh_token:
            # Verify and decode the refresh token
            payload = verify_refresh_token(refresh_token)
            if payload:
                token_jti = payload.get("jti")
                if token_jti:
                    revoke_refresh_token(token_jti)
        
        # Clear cookies regardless of token validity
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        
        return {"message": "Successfully logged out"}
    except Exception as e:
        # Always clear cookies even if there's an error
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@auth_root.post("/logout-all")
async def logout_all_devices(request: Request, response: Response):
    """Logout user from all devices by revoking all refresh tokens"""
    try:
        # Get refresh token from cookies
        refresh_token = request.cookies.get("refresh_token")
        
        if not refresh_token:
            # Clear cookies and return error
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No refresh token provided"
            )
        
        # Verify and decode the refresh token
        payload = verify_refresh_token(refresh_token)
        if not payload:
            # Clear cookies and return error
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("user_id")
        if user_id:
            revoke_all_user_refresh_tokens(user_id)
        
        # Clear current device cookies
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        
        return {"message": "Successfully logged out from all devices"}
    except HTTPException:
        raise
    except Exception as e:
        # Always clear cookies even if there's an error
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
