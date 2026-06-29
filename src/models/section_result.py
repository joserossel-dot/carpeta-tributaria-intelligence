from pydantic import BaseModel


class SectionResult(BaseModel):
    secciones: dict[str, list[int]]
