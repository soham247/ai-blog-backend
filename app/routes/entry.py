from fastapi import APIRouter

entry_root = APIRouter()

# endpoint
@entry_root.get("/")
def api_running():
    return {
        "status": 200,
        "message": "API is running...",
    }