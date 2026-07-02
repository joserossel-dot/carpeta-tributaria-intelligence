from src.analyzers.analysis_result import AnalysisResult
from src.kpis.kpi_result import KPIResult
from src.models.activity import Activity
from src.models.contributor import Contributor
from src.models.f29 import F29
from src.models.tax_folder import Metadata, TaxFolder
from src.reports.executive_report import ExecutiveReport


class TestExecutiveReport:
    def _make_report(
        self,
        tax_folder: TaxFolder | None = None,
        kpis: KPIResult | None = None,
        analysis: AnalysisResult | None = None,
    ) -> str:
        if tax_folder is None:
            tax_folder = TaxFolder(
                metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
            )
        if kpis is None:
            kpis = KPIResult()
        if analysis is None:
            analysis = AnalysisResult()
        return ExecutiveReport().generate(tax_folder, kpis, analysis)

    def test_header_present(self) -> None:
        report = self._make_report()
        assert "# Informe Ejecutivo — Carpeta Tributaria" in report

    def test_general_data_with_contributor(self) -> None:
        tf = TaxFolder(
            contributor=Contributor(
                rut="12.345.678-9",
                razon_social="EMPRESA SPA",
                domicilio="Calle 123",
                comuna="Santiago",
                region="Metropolitana",
                fecha_generacion="01/01/2026",
                fecha_inicio_actividades="15/03/2010",
            ),
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        report = self._make_report(tax_folder=tf)
        assert "**RUT:** 12.345.678-9" in report
        assert "**Razón Social:** EMPRESA SPA" in report
        assert "**Domicilio:** Calle 123" in report
        assert "**Comuna:** Santiago" in report
        assert "**Región:** Metropolitana" in report
        assert "**Fecha Generación:** 01/01/2026" in report
        assert "**Inicio Actividades:** 15/03/2010" in report

    def test_general_data_no_contributor(self) -> None:
        report = self._make_report()
        assert "No disponible" in report

    def test_principal_activity(self) -> None:
        kpis = KPIResult(principal_activity="CULTIVO DE TRIGO")
        report = self._make_report(kpis=kpis)
        assert "CULTIVO DE TRIGO" in report

    def test_principal_activity_not_available(self) -> None:
        report = self._make_report()
        assert "No disponible" in report

    def test_tax_regime_present(self) -> None:
        tf = TaxFolder(
            contributor=Contributor(regimen_tributario="REGIMEN PRO PYME GENERAL (14D)"),
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        report = self._make_report(tax_folder=tf)
        assert "REGIMEN PRO PYME GENERAL (14D)" in report

    def test_tax_regime_not_available(self) -> None:
        report = self._make_report()
        assert "No disponible" in report

    def test_company_age(self) -> None:
        kpis = KPIResult(company_age_years=15.5)
        tf = TaxFolder(
            contributor=Contributor(fecha_inicio_actividades="01/01/2010"),
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        report = self._make_report(tax_folder=tf, kpis=kpis)
        assert "15.5 años" in report
        assert "01/01/2010" in report

    def test_company_age_not_available(self) -> None:
        report = self._make_report()
        assert "No disponible" in report

    def test_f29_summary(self) -> None:
        kpis = KPIResult(f29_count=5, first_f29_period="2024-01", last_f29_period="2024-05", declared_months=5)
        report = self._make_report(kpis=kpis)
        assert "**Total declaraciones:** 5" in report
        assert "**Primer período:** 2024-01" in report
        assert "**Último período:** 2024-05" in report
        assert "**Meses declarados:** 5" in report

    def test_f29_summary_empty(self) -> None:
        report = self._make_report()
        assert "**Total declaraciones:** 0" in report

    def test_statistics(self) -> None:
        analysis = AnalysisResult(statistics={"total_actividades": 3, "total_f29": 2})
        report = self._make_report(analysis=analysis)
        assert "**Total_actividades:** 3" in report or "**Total actividades:** 3" in report
        assert "**Total_f29:** 2" in report or "**Total f29:** 2" in report

    def test_alerts_and_warnings(self) -> None:
        analysis = AnalysisResult(
            alerts=["Contribuyente sin inicio de actividades"],
            warnings=["F29 con períodos faltantes"],
        )
        report = self._make_report(analysis=analysis)
        assert "Contribuyente sin inicio de actividades" in report
        assert "F29 con períodos faltantes" in report

    def test_no_alerts_or_warnings(self) -> None:
        report = self._make_report()
        assert "Sin alertas" in report
        assert "Sin advertencias" in report

    def test_generate_from_real_pdf(self) -> None:
        from src.core.tax_folder_engine import TaxFolderEngine

        engine = TaxFolderEngine("examples/CPTAgrGonzalezLtda.pdf")
        result = engine.parse()
        markdown = ExecutiveReport().generate(result, result.kpis, result.analysis)
        assert markdown.startswith("# Informe Ejecutivo")
        assert "AGRICOLA GONZALEZ" in markdown or "GONZALEZ" in markdown
        assert "RUT:" in markdown
        assert "Actividad Principal" in markdown
        assert "Resumen de F29" in markdown
        assert "Estadísticas" in markdown

    def test_generate_cli_script(self) -> None:
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "scripts/generate_report.py", "examples/CPTAgrGonzalezLtda.pdf"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Reporte generado:" in result.stdout

    def test_cli_no_args(self) -> None:
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "scripts/generate_report.py"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "Uso:" in result.stderr

    def test_cli_invalid_path(self) -> None:
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "scripts/generate_report.py", "nonexistent.pdf"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "Error:" in result.stderr
