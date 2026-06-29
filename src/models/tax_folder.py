from pydantic import BaseModel

from src.models.contributor import Contributor
from src.models.f29 import F29
from src.models.section_result import SectionResult


class TaxFolderMetadata(BaseModel):
    pages: int
    processed_at: str
    version: str


class TaxFolder(BaseModel):
    contributor: Contributor
    f29: list[F29] = []
    sections: SectionResult
    metadata: TaxFolderMetadata
