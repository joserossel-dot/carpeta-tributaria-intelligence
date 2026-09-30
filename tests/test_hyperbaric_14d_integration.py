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
        """Verifica que la empresa con pérdida y CPT negativo active bloqueo por falta de información reciente."""
        cr = hyperbaric_folder.credit_risk
        assert cr is not None
        assert cr.score_compuesto == 58
        assert cr.decision.desempeno_tributario_texto == "Capacidad Operativa Tributaria Baja"
        assert cr.clasificacion_riesgo == "NO EVALUABLE (Falta Información Reciente)"
        assert cr.linea_inicial_sugerida == 0
        assert cr.linea_maxima_sugerida == 0

        mem = cr.decision.memoria_calculo
        assert mem["rli_declarada_le_zero"] is True
        assert "Cód. 1450" in mem["glosa_b2"]
        assert mem["capital_propio_tributario"] == -4_628_691
        assert mem["tope_patrimonial_3pct_cpt"] == 0
        assert "Bloqueo por CPTS Negativo o igual a cero (Cód. 1546: -M$ 4.629 -> Tope Patrimonial M$ 0)" in mem["glosa_paso_d"]
        assert mem["techo_operativo_8pct"] == 585_831
        assert "Costo proxy 30% s/ventas exentas (Compras afectas F29: M$ 1.003/mes)" in mem["glosa_paso_a"]

    def test_pdf_layout_14d(self, hyperbaric_folder):
        """Verifica que el PDF imprima encabezados y códigos dinámicos del régimen 14D."""
        pdf_bytes = PDFReport().generate(hyperbaric_folder)
        assert len(pdf_bytes) > 10_000

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            p1 = pdf.pages[0].extract_text()
            p1_clean = " ".join(p1.split())
            assert "REGIMEN PRO PYME GENERAL (14D)" in p1_clean
            assert "NO EVALUABLE (Falta Información Reciente)" in p1_clean
            assert "Capacidad Operativa Tributaria Baja" in p1_clean
            assert "Fecha Emisión Informe:" in p1_clean
            assert "Cód. 1450" in p1_clean
            assert "CV: 35.0%" in p1_clean
            assert "Giro exento de IVA (Débito 12M: M$ 0)" in p1_clean
            assert "Compras afectas F29: 4.1% de ventas; requiere EERR/Balance" in p1_clean
            assert "Paso B1: Techo por Volumen de Compras (8% C_base)" in p1_clean
            assert "Costo proxy 30% s/ventas exentas (Compras afectas F29: M$ 1.003/mes)" in p1_clean
            assert "M$ 586" in p1_clean
            assert "Paso D: Referencia Patrimonial (3% × CPT de" in p1_clean
            assert "Bloqueo por CPTS Negativo o igual a cero (Cód. 1546: -M$ 4.629" in p1_clean
            assert "NO CONCILIABLE" in p1_clean
            assert "Carpeta sin F22 AT 2025 ni AT 2026" in p1_clean
            assert "Operación en suspenso" in p1_clean
            assert "Quiebra" not in p1_clean

            p2 = pdf.pages[1].extract_text()
            p2_clean = " ".join(p2.split())
            assert "Margen RLI -11.4%" in p2_clean
            assert "aclarar la causa de la pérdida tributaria" in p2_clean
            assert "Declaraciones Anuales F22 AT 2025 y AT 2026 no incluidas en" in p2_clean
            assert "carpeta tributaria (último F22 disponible: AT 2024)" in p2_clean
            assert "M$ 1.003" in p2_clean
            assert "M$ 12.034" in p2_clean
            assert "Ingresos Giro Cód. 1400 (M$)" in p2_clean
            assert "Base Imponible / Pérdida Cód. 1440/1450 (M$)" in p2_clean
            assert "Capital Propio CPTS Cód. 1545/1546" in p2_clean
            assert "M$ 40.492" in p2_clean
            assert "-M$ 4.629 (Cód. 1450)" in p2_clean
            assert "-M$ 4.629 (Cód. 1546)" in p2_clean
            assert "NO CONCILIABLE — Carpeta sin F22 AT 2025 ni AT 2026 (último F22 disponible: AT 2024; año 2023 con solo 7 meses F29 en carpeta)" in p2_clean
            assert "D=3% CPT (CPT<=0 -> M$ 0)" in p2_clean
            assert "Quiebra" not in p2_clean
