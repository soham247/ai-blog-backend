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


def DecodeBlogWithAuthor(blog) -> dict:
    """
    Decode a single blog document with populated author details
    """
    return {
        "id": str(blog["_id"]),
        "title": blog["title"],
        "sub_title": blog["sub_title"],
        "content": blog["content"],
        "tags": blog["tags"],
        "created_at": blog["created_at"],
        "author": {
            "id": str(blog["author"]["_id"]) if blog.get("author") and blog["author"].get("_id") else None,
            "fullname": blog["author"].get("fullname") if blog.get("author") else None,
            "email": blog["author"].get("email") if blog.get("author") else None
        }
    }

def DecodeBlogsWithAuthor(blogs) -> list:
    """
    Decode multiple blog documents with populated author details
    """
    return [DecodeBlogWithAuthor(blog) for blog in blogs]