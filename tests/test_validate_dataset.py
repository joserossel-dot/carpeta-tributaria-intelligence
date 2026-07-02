import subprocess
import sys
from pathlib import Path


class TestValidateDataset:
    def test_script_generates_report(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_dataset.py"],
            capture_output=True,
            text=True,
            timeout=300,
        )
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
        report = Path("output/validation_report.md")
        assert report.exists()
        content = report.read_text(encoding="utf-8")

        assert "Exitosos:" in content
        assert "Con errores:" in content
        assert "Tiempo promedio:" in content
        assert "Tiempo máximo:" in content

    def test_report_lists_all_pdfs(self) -> None:
        report = Path("output/validation_report.md")
        content = report.read_text(encoding="utf-8")

        expected_pdfs = [
            "CPTAgrGonzagriLtda.pdf",
            "CPTAgrGonzalezLtda.pdf",
            "CPTExportadora.pdf",
            "CPTGonzagriS.A..pdf",
        ]
        for pdf in expected_pdfs:
            assert pdf in content, f"{pdf} not found in report"

        assert "HYPERBARIC" in content
        assert "PROTERM S.A." in content

    def test_report_has_missing_fields_table(self) -> None:
        report = Path("output/validation_report.md")
        content = report.read_text(encoding="utf-8")

        table_markers = [
            "| Campo",
            "|-------",
            "Región",
            "Representantes",
            "Propiedades",
            "Vehículos",
        ]
        for marker in table_markers:
            assert marker in content, f"Missing field marker '{marker}' not in report"

    def test_report_identifies_success_and_failure_count(self) -> None:
        report = Path("output/validation_report.md")
        content = report.read_text(encoding="utf-8")

        assert "Exitosos:" in content
        assert "5" in content  # 5 valid PDFs expected

    def test_script_stdout_shows_progress(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_dataset.py"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert "Procesando" in result.stdout
        assert "OK" in result.stdout
        assert "ERROR" in result.stdout
        assert "exitosos" in result.stdout
        assert "fallidos" in result.stdout
