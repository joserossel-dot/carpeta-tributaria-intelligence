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
            return tax_folder.model_dump(mode="json")

        data = tax_folder.model_dump(mode="json")
        if tax_folder.contributor is not None:
            data["contributor"] = normalize_contributor(tax_folder.contributor).model_dump(mode="json")
        if tax_folder.f29:
            data["f29"] = [f.model_dump(mode="json") for f in normalize_f29(tax_folder.f29)]
        return data
