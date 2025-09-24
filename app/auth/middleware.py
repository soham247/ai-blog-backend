from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable


class TokenRefreshMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically update access token cookies when they are refreshed
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Check if a new access token was generated during the request
        if hasattr(request.state, 'new_access_token'):
            # Update the access token cookie
            response.set_cookie(
                key="access_token",
                value=request.state.new_access_token,
                max_age=15 * 60,  # 15 minutes
                httponly=True,
                secure=True,  # Set to True in production with HTTPS
                samesite="lax"
            )
        
        return response