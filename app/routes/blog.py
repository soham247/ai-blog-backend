from fastapi import APIRouter
from app.models.blog import Blog, UpdateBlog
from app.config.database import blogs_collection
from app.serializers.blog import DecodeBlog, DecodeBlogs
import datetime
from bson import ObjectId

blog_root = APIRouter(prefix="/blog")

@blog_root.post("/")
def create_blog(doc: Blog):
    doc = dict(doc)
    doc["created_at"] = datetime.datetime.now()
    
    res = blogs_collection.insert_one(doc)

    if res.acknowledged == False:
        return {
            "status": "error",
            "message": "Something went wrong"
        }
        
    return {
        "status": "ok",
        "id": str(res.inserted_id),
        "message": "Blog created successfully"
    }
    
@blog_root.get("/{id}")
def get_blog(id: str):
    blog = blogs_collection.find_one({"_id": ObjectId(id)})
    decoded_blog = DecodeBlog(blog) if blog else None   
    
    return {
        "status": "ok",
        "data": decoded_blog
    }
    
@blog_root.get("/")
def get_blogs():
    res = blogs_collection.find()
    decoded_blogs = DecodeBlogs(res)
    
    return {
        "status": "ok",
        "data": decoded_blogs
    }

@blog_root.patch("/{id}")
def update_blog(id: str, doc: UpdateBlog):
    req = dict(doc.model_dump(exclude_unset=True))

    res = blogs_collection.find_one_and_update({"_id": ObjectId(id)}, {"$set": req})

    if res.acknowledged == False:
        return {
            "status": "error",
            "message": "Something went wrong"
        }
        
    return {
        "status": "ok",
        "message": "Blog updated successfully"
    }

@blog_root.delete("/{id}")
def delete_blog(id: str):
    res = None
    try:
        res = blogs_collection.find_one_and_delete({"_id": ObjectId(id)})
    except:
        return {
            "status": "error",
            "message": "Invalid blog id"
        }
    
    if res is None:
        return {
            "status": "error",
            "message": "Blog not found"
        }
        
    return {
        "status": "ok",
        "message": "Blog deleted successfully"
    }