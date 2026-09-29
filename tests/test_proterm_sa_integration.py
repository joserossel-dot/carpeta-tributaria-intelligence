import io
from pathlib import Path
import pdfplumber
import pytest

from src.core.tax_folder_engine import TaxFolderEngine
from src.reports.pdf_report import PDFReport

_PROTERM_CANDIDATES = [
    Path("/Users/josealfonsorossel/Downloads/Carpeta_Tributaria_Regular (4).pdf"),
    Path("examples/Carpeta_Tributaria_Regular (4).pdf"),
]
PROTERM_PDF = next((p for p in _PROTERM_CANDIDATES if p.exists()), Path("examples/Carpeta_Tributaria_Regular (4).pdf"))


@pytest.mark.skipif(not PROTERM_PDF.exists(), reason="PDF de prueba PROTERM S.A. no disponible")
class TestProtermSaIntegration:
    @pytest.fixture(scope="class")
    def proterm_folder(self):
        engine = TaxFolderEngine(str(PROTERM_PDF))
        return engine.parse()

    def test_contributor_info(self, proterm_folder):
        """Verifica la extracción limpia del contribuyente, comuna y región del Biobío."""
        contrib = proterm_folder.contributor
        assert contrib is not None
        assert contrib.rut == "78155540-1"
        assert contrib.razon_social == "PROTERM S.A."
        assert contrib.comuna == "CONCEPCION"
        assert contrib.region == "REGIÓN DEL BIOBÍO"
        assert "AVDA. INGLESA 55 PEDRO DE VALDIVIA" in (contrib.domicilio or "")

    def test_f22_positive_rli(self, proterm_folder):
        """Verifica que el último F22 (AT 2026) extraiga RLI positiva con Cód. 1694."""
        assert len(proterm_folder.f22) == 3
        f22_by_ano = {f.anio_tributario: f for f in proterm_folder.f22}
        assert "2026" in f22_by_ano

        f26 = f22_by_ano["2026"]
        assert f26.ingresos == 6398884318
        assert f26.ingresos_source_code == "1657"
        assert f26.renta_liquida_imponible == 837533060
        assert f26.rli_source_code == "1694"
        assert f26.capital_propio_tributario == 2353699152
        assert f26.cpt_source_code in ("1698", "645")

    def test_credit_evaluation_proterm(self, proterm_folder):
        """Verifica que la empresa con RLI positiva no se bloquee por pérdida y obtenga sus líneas escalonadas."""
        cr = proterm_folder.credit_risk
        assert cr is not None
        assert cr.score_compuesto == 94
        assert cr.clasificacion_riesgo == "ELEGIBLE PARA LÍNEA COMERCIAL (FASE 1 TRIBUTARIA)"
        assert cr.evaluacion_referencial == "ELEGIBLE PARA LÍNEA COMERCIAL (FASE 1 TRIBUTARIA) (Línea Sujeta a Dicom)"

        mem = cr.decision.memoria_calculo
        assert mem["rli_declarada_le_zero"] is False
        assert mem["techo_operativo_8pct"] == 13327592
        assert mem["freno_absorcion_operacional"] == 17448605
        assert mem["tope_patrimonial_3pct_cpt"] == 70610975
        assert mem["linea_maxima_condicionada"] == 13300000
        assert mem["linea_inicial_sugerida"] == 6600000

        assert cr.linea_maxima_sugerida == 13300000
        assert cr.linea_inicial_sugerida == 6600000
        assert cr.cupo_aprobado == 6600000

    def test_pdf_layout_proterm(self, proterm_folder):
        """Verifica la generación del PDF con comuna/región sin comas sueltas y memoria coherente."""
        pdf_bytes = PDFReport().generate(proterm_folder)
        assert len(pdf_bytes) > 10_000

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            p1 = pdf.pages[0].extract_text()
            assert "Comuna / Región: CONCEPCION, REGIÓN DEL BIOBÍO" in p1
            assert "Comuna / Región: CONCEPCION, —" not in p1
            assert "ELEGIBLE PARA LÍNEA COMERCIAL" in p1
            assert "Inicial: M$ 6.600" in p1
            assert "Máxima: M$ 13.300" in p1
            assert "M$ 13.328" in p1
            assert "M$ 17.449" in p1
