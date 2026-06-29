from pydantic import BaseModel


class PageResult(BaseModel):
    page: int
    text: str


class ExtractResult(BaseModel):
    pages: list[PageResult]
