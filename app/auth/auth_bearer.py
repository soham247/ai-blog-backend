from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from app.auth.auth_handler import verify_access_token, refresh_access_token


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        # First try to get token from cookies
        access_token = request.cookies.get("access_token")
        
        if not access_token:
            # Fall back to Authorization header for backward compatibility
            try:
                credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
                if credentials and credentials.scheme == "Bearer":
                    access_token = credentials.credentials
            except HTTPException:
                pass
        
        if not access_token:
            raise HTTPException(status_code=401, detail="No access token provided")
        
        # Verify the access token
        payload = self.verify_jwt(access_token)
        if not payload:
            # Access token is invalid/expired, try to refresh automatically
            refresh_token = request.cookies.get("refresh_token")
            if refresh_token:
                new_tokens = refresh_access_token(refresh_token)
                if new_tokens:
                    # Set the new access token in request state for potential cookie update
                    request.state.new_access_token = new_tokens["access_token"]
                    # Verify the new access token
                    payload = self.verify_jwt(new_tokens["access_token"])
                    if payload:
                        return payload
            
            raise HTTPException(status_code=401, detail="Invalid or expired access token")
        
        return payload

    def verify_jwt(self, jwtoken: str) -> dict:
        """
        Verify access token specifically and return the payload if valid, None if invalid
        """
        try:
            payload = verify_access_token(jwtoken)
            return payload
        except Exception:
            return None
