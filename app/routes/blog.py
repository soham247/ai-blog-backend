from fastapi import APIRouter, HTTPException, status
from app.models.blog import Blog, UpdateBlog
from app.config.database import blogs_collection
from app.serializers.blog import DecodeBlog, DecodeBlogs
import datetime
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import PyMongoError

blog_root = APIRouter(prefix="/blog")

@blog_root.post("/")
def create_blog(doc: Blog):
    try:
        doc = dict(doc)
        doc["created_at"] = datetime.datetime.now()
        
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
def get_blog(id: str):
    try:
        blog = blogs_collection.find_one({"_id": ObjectId(id)})
        
        if blog is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog not found"
            )
            
        decoded_blog = DecodeBlog(blog)
        
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
def get_blogs():
    try:
        res = blogs_collection.find()
        decoded_blogs = DecodeBlogs(res)
        
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
def update_blog(id: str, doc: UpdateBlog):
    try:
        req = dict(doc.model_dump(exclude_unset=True))
        
        if not req:  # No fields to update
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update"
            )

        res = blogs_collection.find_one_and_update(
            {"_id": ObjectId(id)}, 
            {"$set": req}
        )

        if res is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog not found"
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
def delete_blog(id: str):
    try:
        res = blogs_collection.find_one_and_delete({"_id": ObjectId(id)})
        
        if res is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog not found"
            )
            
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