import json
import tempfile
from pathlib import Path

from src.models.contributor import Contributor
from src.models.f29 import F29, F29Detail
from src.models.tax_folder import Metadata, TaxFolder


def _make_fake_tax_folder(**overrides: str | None) -> TaxFolder:
    contributor = Contributor(
        rut=overrides.get("rut", "79.606.270-3"),
        razon_social=overrides.get("razon_social", "  AGRICOLA  GONZAGRI  LIMITADA  "),
        fecha_generacion=overrides.get("fecha_generacion", "30/01/2020 10:40"),
        fecha_inicio_actividades=overrides.get("fecha_inicio_actividades", "  Anterior a 1993  "),
        domicilio=overrides.get("domicilio", "  FUNDO SANTA MARTA S/N\nMOLINA  "),
        comuna=overrides.get("comuna", "  molina  "),
        region=overrides.get("region"),
        tipo_contribuyente=overrides.get("tipo_contribuyente", "Primera categoría"),
        regimen_tributario=overrides.get("regimen_tributario"),
    )
    f29 = F29(
        periodo="12/2019",
        folio="123456",
        fecha_presentacion="28/01/2020",
        detalles=[
            F29Detail(codigo="503", glosa="  CANTIDAD  FACTURAS  ", valor="  236.141.139  "),
            F29Detail(codigo="502", glosa="  DÉBITOS  ", valor="1,60"),
        ],
    )
    metadata = Metadata(source_file="test.pdf", pages=10, processing_time=0.123)
    return TaxFolder(contributor=contributor, f29=[f29], metadata=metadata)


class TestJsonExporter:
    def test_export_default_normalize(self) -> None:
        from src.exporters.json_exporter import JsonExporter

        folder = _make_fake_tax_folder()
        exporter = JsonExporter()

        with tempfile.TemporaryDirectory() as tmp:
            path = exporter.export(folder, Path(tmp) / "out.json")
            assert path.exists()
            data = json.loads(path.read_text(encoding="utf-8"))

        assert data["contributor"]["rut"] == "79606270-3"
        assert data["contributor"]["razon_social"] == "AGRICOLA GONZAGRI LIMITADA"
        assert data["contributor"]["comuna"] == "MOLINA"
        assert data["f29"][0]["periodo"] == "2019-12"
        assert data["f29"][0]["detalles"][0]["valor"] == "236141139"
        assert data["f29"][0]["detalles"][1]["valor"] == "1.60"
        assert data["metadata"]["source_file"] == "test.pdf"

    def test_export_no_normalize(self) -> None:
        from src.exporters.json_exporter import JsonExporter

        folder = _make_fake_tax_folder()
        exporter = JsonExporter(normalize=False)

        with tempfile.TemporaryDirectory() as tmp:
            path = exporter.export(folder, Path(tmp) / "out.json")
            data = json.loads(path.read_text(encoding="utf-8"))

        assert data["contributor"]["rut"] == "79.606.270-3"
        assert data["contributor"]["razon_social"] == "  AGRICOLA  GONZAGRI  LIMITADA  "
        assert data["f29"][0]["periodo"] == "12/2019"
        assert data["f29"][0]["detalles"][0]["valor"] == "  236.141.139  "

    def test_dumps(self) -> None:
        from src.exporters.json_exporter import JsonExporter

        folder = _make_fake_tax_folder()
        exporter = JsonExporter(normalize=True)
        s = exporter.dumps(folder)
        data = json.loads(s)
        assert data["contributor"]["rut"] == "79606270-3"

    def test_export_creates_parent_dir(self) -> None:
        from src.exporters.json_exporter import JsonExporter

        folder = _make_fake_tax_folder()
        exporter = JsonExporter()

        with tempfile.TemporaryDirectory() as tmp:
            nested = Path(tmp) / "a" / "b" / "out.json"
            exporter.export(folder, nested)
            assert nested.exists()

    def test_custom_indent(self) -> None:
        from src.exporters.json_exporter import JsonExporter

        folder = _make_fake_tax_folder()
        exporter = JsonExporter(indent=4)

        with tempfile.TemporaryDirectory() as tmp:
            path = exporter.export(folder, Path(tmp) / "out.json")
            text = path.read_text(encoding="utf-8")
            assert '    "contributor"' in text
