from fastapi import APIRouter, Body
import datetime

from app.auth.auth_handler import sign_jwt, hash_password, verify_password
from app.models.user import  UserSchema, UserLoginSchema
from app.config.database import users_collection

auth_root = APIRouter(prefix="/user", tags=["user"])

@auth_root.post("/signup")
async def create_user(user: UserSchema = Body(...)):
    try:
        res = users_collection.find_one({"email": user.email})
        if res:
            return {"error": "User with this email already exists"}
        
        hashed_password = hash_password(user.password)
        
        user_data = {
            **user.model_dump(),
            "password": hashed_password,
            "created_at": datetime.datetime.now(),
            "updated_at": datetime.datetime.now()
        }
        
        res = users_collection.insert_one(user_data)
        
        if not res.acknowledged:
            return {"error": "Failed to create user"}
        return sign_jwt(user.email)
    except Exception as e:
        return {"error": str(e)}
    
@auth_root.post("/login")
async def user_login(user: UserLoginSchema = Body(...)):
    try:
        db_user = users_collection.find_one({"email": user.email})
        
        # Check if user exists and password is correct
        if not db_user:
            return {"error": "Invalid email or password"}
        
        if not verify_password(user.password, db_user["password"]):
            return {"error": "Invalid email or password"}
        
        return sign_jwt(user.email)
        
    except Exception as e:
        return {"error": str(e)}