def DecodeBlog(data) -> dict:
    return {
        "_id": str(data["_id"]),
        "title": data["title"],
        "sub_title": data["sub_title"],
        "content": data["content"],
        "author": data["author"],
        "tags": data["tags"],
        "created_at": data["created_at"]
    }
    
def DecodeBlogs(data) -> list:
    return [DecodeBlog(blog) for blog in data]