import io
from pathlib import Path
import pdfplumber
import pytest

from src.core.tax_folder_engine import TaxFolderEngine
from src.reports.pdf_report import PDFReport

_HYPERBARIC_CANDIDATES = [
    Path("/Users/josealfonsorossel/Downloads/Carpeta Tributaria.CLINICA HYPERBARIC.pdf"),
    Path("examples/Carpeta Tributaria.CLINICA HYPERBARIC.pdf"),
]
HYPERBARIC_PDF = next((p for p in _HYPERBARIC_CANDIDATES if p.exists()), Path("examples/Carpeta Tributaria.CLINICA HYPERBARIC.pdf"))


@pytest.mark.skipif(not HYPERBARIC_PDF.exists(), reason="PDF de prueba CLINICA HYPERBARIC no disponible")
class TestHyperbaric14DIntegration:
    @pytest.fixture(scope="class")
    def hyperbaric_folder(self):
        engine = TaxFolderEngine(str(HYPERBARIC_PDF))
        return engine.parse()

    def test_contributor_info(self, hyperbaric_folder):
        """Verifica la extracción limpia del contribuyente Pyme 14D."""
        contrib = hyperbaric_folder.contributor
        assert contrib is not None
        assert contrib.rut == "77460385-9"
        assert contrib.razon_social == "CLINICA HYPERBARIC SPA"
        assert "PRO PYME" in (contrib.regimen_tributario or "").upper()
        assert contrib.comuna == "CONCEPCION"
        assert contrib.region == "REGIÓN DEL BIOBÍO"

    def test_f22_14d_codes(self, hyperbaric_folder):
        """Verifica la extracción de códigos específicos del régimen 14D (1400, 1450, 1546)."""
        assert len(hyperbaric_folder.f22) == 1
        f24 = hyperbaric_folder.f22[0]
        assert f24.anio_tributario == "2024"
        assert f24.ingresos == 40_492_300
        assert f24.ingresos_source_code == "1400"
        assert f24.renta_liquida_imponible == -4_628_691
        assert f24.rli_source_code == "1450"
        assert f24.capital_propio_tributario == -4_628_691
        assert f24.cpt_source_code == "1546"

    def test_credit_evaluation_14d(self, hyperbaric_folder):
        """Verifica que la empresa con pérdida y CPT negativo active bloqueo por pérdida tributaria."""
        cr = hyperbaric_folder.credit_risk
        assert cr is not None
        assert cr.score_compuesto == 68
        assert "SIN LÍNEA AUTOMÁTICA" in cr.clasificacion_riesgo
        assert cr.linea_inicial_sugerida == 0
        assert cr.linea_maxima_sugerida == 0

        mem = cr.decision.memoria_calculo
        assert mem["rli_declarada_le_zero"] is True
        assert "Cód. 1450" in mem["glosa_b2"]
        assert mem["capital_propio_tributario"] == -4_628_691

    def test_pdf_layout_14d(self, hyperbaric_folder):
        """Verifica que el PDF imprima encabezados y códigos dinámicos del régimen 14D."""
        pdf_bytes = PDFReport().generate(hyperbaric_folder)
        assert len(pdf_bytes) > 10_000

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            p1 = pdf.pages[0].extract_text()
            assert "REGIMEN PRO PYME GENERAL (14D)" in p1
            assert "SIN LÍNEA AUTOMÁTICA" in p1
            assert "Cód. 1450" in p1

            p2 = pdf.pages[1].extract_text()
            assert "Ingresos Giro Cód. 1400 (M$)" in p2
            assert "Base Imponible / Pérdida Cód. 1440/1450 (M$)" in p2
            assert "Capital Propio CPTS Cód. 645/1545" in p2
            assert "M$ 40.492" in p2
            assert "-M$ 4.629 (Cód. 1450)" in p2
            assert "-M$ 4.629 (Cód. 1546)" in p2
