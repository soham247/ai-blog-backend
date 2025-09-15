from pydantic import BaseModel

class Blog(BaseModel):
    title: str
    sub_title: str
    content: str
    author: str
    tags: list
    
class UpdateBlog(BaseModel):
    title: str | None = None
    sub_title: str | None = None
    content: str | None = None
    author: str | None = None
    tags: list | None = None
    