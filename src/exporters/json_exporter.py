import json
from pathlib import Path

from src.models.tax_folder import TaxFolder
from src.normalizers.contributor_normalizer import normalize_contributor
from src.normalizers.f29_normalizer import normalize_f29


class JsonExporter:
    def __init__(self, normalize: bool = True, indent: int = 2) -> None:
        self.normalize = normalize
        self.indent = indent

    def export(self, tax_folder: TaxFolder, path: str | Path) -> Path:
        output = Path(path)
        data = self._prepare(tax_folder)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(data, indent=self.indent, ensure_ascii=False),
            encoding="utf-8",
        )
        return output

    def dumps(self, tax_folder: TaxFolder) -> str:
        data = self._prepare(tax_folder)
        return json.dumps(data, indent=self.indent, ensure_ascii=False)

    def _prepare(self, tax_folder: TaxFolder) -> dict:
        if not self.normalize:
            return tax_folder.model_dump()

        contributor = normalize_contributor(tax_folder.contributor)
        f29 = normalize_f29(tax_folder.f29)
        sections = tax_folder.sections.model_dump()
        metadata = tax_folder.metadata.model_dump()

        return {
            "contributor": contributor.model_dump(),
            "f29": [f.model_dump() for f in f29],
            "sections": sections,
            "metadata": metadata,
        }
