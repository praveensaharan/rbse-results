from pydantic import BaseModel


class SearchRequest(BaseModel):
    name: str
    url: str
