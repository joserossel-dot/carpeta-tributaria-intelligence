from pydantic import BaseModel


class PageResult(BaseModel):
    page: int
    text: str
    tables: list[list[list[str | None]]] = []
    column_text: str | None = None


class ExtractResult(BaseModel):
    pages: list[PageResult]
