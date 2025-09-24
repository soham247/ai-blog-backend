from fastapi import FastAPI

from app.routes.entry import entry_root
from app.routes.blog import blog_root
from app.routes.auth import auth_root
from app.auth.middleware import TokenRefreshMiddleware

app = FastAPI()

# Add middleware for automatic token refresh
app.add_middleware(TokenRefreshMiddleware)

app.include_router(entry_root)
app.include_router(blog_root)
app.include_router(auth_root)
