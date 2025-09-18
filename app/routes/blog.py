from fastapi import APIRouter, HTTPException, status, Body, Depends
from app.models.blog import Blog, UpdateBlog
from app.config.database import blogs_collection
from app.serializers.blog import DecodeBlog, DecodeBlogs, DecodeBlogWithAuthor, DecodeBlogsWithAuthor
import datetime
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import PyMongoError

from app.auth.auth_bearer import JWTBearer

blog_root = APIRouter(prefix="/blog", tags=["blog"])

@blog_root.post("/")
def create_blog(doc: Blog, token_payload: dict = Depends(JWTBearer())):
    try:
        doc = dict(doc)
        doc["created_at"] = datetime.datetime.now()
        
        # Convert user_id string to ObjectId for proper referencing
        user_id = token_payload.get("user_id")  # Adjust field name based on your JWT payload structure
        doc["author"] = ObjectId(user_id)
        
        res = blogs_collection.insert_one(doc)

        if not res.acknowledged:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create blog"
            )
            
        return {
            "status": "ok",
            "id": str(res.inserted_id),
            "message": "Blog created successfully"
        }
    except PyMongoError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e._message)
        )
    
@blog_root.get("/{id}")
def get_blog(id: str, token_payload: dict = Depends(JWTBearer())):
    try:
        # Use aggregation to populate author details
        pipeline = [
            {"$match": {"_id": ObjectId(id)}},
            {
                "$lookup": {
                    "from": "users",  # Change this to your actual users collection name
                    "localField": "author",
                    "foreignField": "_id",
                    "as": "author_details"
                }
            },
            {
                "$unwind": {
                    "path": "$author_details",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$project": {
                    "title": 1,
                    "sub_title": 1,
                    "content": 1,
                    "tags": 1,
                    "created_at": 1,
                    "author": {
                        "_id": "$author_details._id",
                        "fullname": "$author_details.fullname",  # Adjust field names based on your user schema
                        "email": "$author_details.email"        # Add other fields you want to include
                    }
                }
            }
        ]
        
        result = list(blogs_collection.aggregate(pipeline))
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog not found"
            )
            
        blog = result[0]
        
        # Use the serializer function instead of manual conversion
        decoded_blog = DecodeBlogWithAuthor(blog)
        
        return {
            "status": "ok",
            "data": decoded_blog
        }
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid blog ID format"
        )
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    
@blog_root.get("/")
def get_blogs(token_payload: dict = Depends(JWTBearer()), user_only: bool = False):
    try:
        # Build match stage based on user_only parameter
        match_stage = {}
        if user_only:
            match_stage = {"author": ObjectId(token_payload.get("user_id"))}
        
        # Aggregation pipeline to populate author details
        pipeline = [
            {"$match": match_stage},
            {
                "$lookup": {
                    "from": "users",  # Change this to your actual users collection name
                    "localField": "author",
                    "foreignField": "_id",
                    "as": "author_details"
                }
            },
            {
                "$unwind": {
                    "path": "$author_details",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$project": {
                    "title": 1,
                    "sub_title": 1,
                    "content": 1,
                    "tags": 1,
                    "created_at": 1,
                    "author": {
                        "_id": "$author_details._id",
                        "fullname": "$author_details.fullname",  # Adjust field names based on your user schema
                        "email": "$author_details.email"        # Add other fields you want to include
                    }
                }
            },
            {"$sort": {"created_at": -1}}  # Sort by newest first
        ]
        
        blogs = list(blogs_collection.aggregate(pipeline))
        
        # Use the serializer function instead of manual conversion
        decoded_blogs = DecodeBlogsWithAuthor(blogs)
        
        return {
            "status": "ok",
            "data": decoded_blogs
        }
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@blog_root.patch("/{id}")
def update_blog(id: str, doc: UpdateBlog, token_payload: dict = Depends(JWTBearer())):
    try:
        req = dict(doc.model_dump(exclude_unset=True))
        
        if not req:  # No fields to update
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update"
            )

        # Authorization check: ensure user can only update their own blogs
        existing_blog = blogs_collection.find_one({"_id": ObjectId(id)})
        if not existing_blog:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog not found"
            )
        
        if existing_blog.get("author") != ObjectId(token_payload.get("user_id")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Not authorized to update this blog"
            )

        # Don't allow updating the author field through this endpoint
        if "author" in req:
            del req["author"]

        res = blogs_collection.find_one_and_update(
            {"_id": ObjectId(id)}, 
            {"$set": req}
        )
            
        return {
            "status": "ok",
            "message": "Blog updated successfully"
        }
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid blog ID format"
        )
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@blog_root.delete("/{id}")
def delete_blog(id: str, token_payload: dict = Depends(JWTBearer())):
    try:
        # Authorization check: ensure user can only delete their own blogs
        existing_blog = blogs_collection.find_one({"_id": ObjectId(id)})
        if not existing_blog:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog not found"
            )
        
        if existing_blog.get("author") != ObjectId(token_payload.get("user_id")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Not authorized to delete this blog"
            )
        
        res = blogs_collection.find_one_and_delete({"_id": ObjectId(id)})
            
        return {
            "status": "ok",
            "message": "Blog deleted successfully"
        }
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid blog ID format"
        )
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )