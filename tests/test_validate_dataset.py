import subprocess
import sys
from pathlib import Path

FIXTURE_DIR = "tests/fixtures_validate"


def _run_validate() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "scripts/validate_dataset.py", FIXTURE_DIR],
        capture_output=True,
        text=True,
        timeout=300,
    )


class TestValidateDataset:
    """Corre validate_dataset.py contra un fixture propio y deterministico
    (tests/fixtures_validate/), NO contra examples/. examples/ es una
    carpeta de muestras de uso general que cualquiera puede editar/limpiar
    -- acoplar el test a su composicion (cuantos archivos hay, cuales
    estan corruptos) lo vuelve fragil ante cambios legitimos ahi.
    """

    def test_script_generates_report(self) -> None:
        result = _run_validate()
        assert result.returncode == 0

        report = Path("output/validation_report.md")
        assert report.exists()
        content = report.read_text(encoding="utf-8")

        assert "# Informe de Validación" in content
        assert "## Resumen General" in content
        assert "## Detalle por Archivo" in content
        assert "## Archivos con Errores" in content
        assert "## Campos con Mayor Porcentaje de Valores Faltantes" in content
        assert "✅ OK" in content
        assert "❌ ERROR" in content

    def test_report_has_statistics(self) -> None:
        _run_validate()
        content = Path("output/validation_report.md").read_text(encoding="utf-8")

        assert "Exitosos:" in content
        assert "Con errores:" in content
        assert "Tiempo promedio:" in content
        assert "Tiempo máximo:" in content

    def test_report_lists_all_pdfs(self) -> None:
        _run_validate()
        content = Path("output/validation_report.md").read_text(encoding="utf-8")

        for pdf in ["CPTAgrGonzalezLtda.pdf", "CPTExportadora.pdf", "CPTGonzagriS.A..pdf", "corrupto.pdf"]:
            assert pdf in content, f"{pdf} not found in report"

        assert "AGRICOLA GONZALEZ LIMITADA" in content
        assert "EXPORTADORA GONZAGRI S A" in content
        assert "GONZAGRI S.A." in content

    def test_report_has_missing_fields_table(self) -> None:
        _run_validate()
        content = Path("output/validation_report.md").read_text(encoding="utf-8")

        table_markers = [
            "| Campo",
            "|-------",
            "Región",
            "Propiedades",
            "Vehículos",
        ]
        for marker in table_markers:
            assert marker in content, f"Missing field marker '{marker}' not in report"

    def test_report_identifies_success_and_failure_count(self) -> None:
        _run_validate()
        content = Path("output/validation_report.md").read_text(encoding="utf-8")

        # 3 PDFs reales validos + 1 corrupto sintetico -> 3 exitosos, 1 con error.
        assert "**Exitosos:** 3" in content
        assert "**Con errores:** 1" in content
        assert "- **corrupto.pdf:**" in content

    def test_script_stdout_shows_progress(self) -> None:
        result = _run_validate()
        assert "Procesando" in result.stdout
        assert "OK" in result.stdout
        assert "ERROR" in result.stdout
        assert "exitosos" in result.stdout
        assert "fallidos" in result.stdout
        assert "3 exitosos, 1 fallidos" in result.stdout
