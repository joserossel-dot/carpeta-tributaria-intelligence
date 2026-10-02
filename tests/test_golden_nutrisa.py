import io
from pathlib import Path
import pdfplumber
import pytest

from src.models.tax_folder import TaxFolder
from src.credit.credit_risk_engine import CreditRiskEngine
from src.reports.pdf_report import PDFReport

NUTRISA_FIXTURE = Path(__file__).parent / "fixtures" / "cases" / "nutrisa.json"


class TestGoldenNutrisa:
    @pytest.fixture(scope="class")
    def nutrisa_folder(self):
        folder = TaxFolder.model_validate_json(NUTRISA_FIXTURE.read_text(encoding="utf-8"))
        folder.credit_risk = CreditRiskEngine().calculate(folder)
        return folder

    def test_representantes_multilinea_y_forma_actuacion(self, nutrisa_folder):
        """Verifica la extracción limpia de los 3 representantes de la empresa y la forma de actuación."""
        corp = nutrisa_folder.corporate_info
        assert corp is not None
        assert corp.forma_actuacion_representantes == "En conjunto"

        reps = corp.representantes
        assert len(reps) == 3

        nombres = [r.nombre for r in reps]
        assert "REPRESENTANTE 1" in nombres
        assert "REPRESENTANTE 2" in nombres
        assert "REPRESENTANTE 3" in nombres

        ruts = {r.nombre: r.rut for r in reps}
        assert ruts["REPRESENTANTE 1"] == "11111111-1"
        assert ruts["REPRESENTANTE 2"] == "22222222-2"
        assert ruts["REPRESENTANTE 3"] == "15555555-6"

        for r in reps:
            assert r.forma_actuacion == "En conjunto"
            assert r.vigente is True

    def test_evaluacion_crediticia_v26_perfil_solido(self, nutrisa_folder):
        """Verifica la clasificación v3.0.0+: Carpeta Vencida > 60 días bloquea la línea comercial."""
        cr = nutrisa_folder.credit_risk
        assert cr is not None
        assert cr.clasificacion_riesgo == "NO EVALUABLE (Carpeta Vencida > 60 días)"
        assert cr.evaluacion_referencial == "NO EVALUABLE (Carpeta Vencida > 60 días)"

        # Líneas bloqueadas a M$ 0 por carpeta vencida (> 60 días)
        assert cr.linea_maxima_condicionada == 0
        assert cr.linea_inicial_sugerida == 0
        assert cr.cupo_aprobado == 0
        assert cr.plazo_inicial_sugerido == "Contado (0 días)"

    def test_memoria_calculo_nutrisa(self, nutrisa_folder):
        """Verifica la consistencia cuantitativa de la Memoria de Cálculo."""
        mem = nutrisa_folder.credit_risk.memoria_calculo
        assert mem is not None

        # Freno B2 debe ser min(15% Spread F29, 25% RLI Mensualizada F22)
        # 25% RLI Mensualizada: 0.25 * (692.055.540 / 12) = 14.417.824
        # Techo B1: 8% Compras = 28.162.864
        # Freno flujo < Techo compras -> el freno gobierna
        assert mem["rli_ultimo_f22"] == 692_055_540
        assert mem["capital_propio_tributario"] == 3_625_109_624
        assert mem["base_compras_c_base"] == 523_884_831
        assert mem["techo_operativo_8pct"] == 41_910_786
        assert mem["freno_absorcion_operacional"] == 14_417_824
        assert mem["linea_maxima_condicionada"] == 0
        assert mem["linea_inicial_sugerida"] == 0

        # CPT holgado (Tope patrimonial 3% CPT no restrictivo)
        assert mem["tope_patrimonial_3pct_cpt"] == 108_753_289

    def test_filtro_elegibilidad_y_resguardo_nutrisa(self, nutrisa_folder):
        """Verifica que el filtro de elegibilidad y resguardo incluyan la actuación conjunta y representantes."""
        cr = nutrisa_folder.credit_risk
        filtro = cr.filtro_elegibilidad
        rep_filtro = next((item for item in filtro if "Representantes Legales" in item.get("parametro", "")), None)
        assert rep_filtro is not None
        assert "En conjunto" in rep_filtro.get("detalle", "")
        assert "3 representante(s) registrado(s)" in rep_filtro.get("detalle", "")

        resguardo = cr.resguardo_comercial_sugerido
        assert "Operación bloqueada. Se exige actualización de carpeta al mes en curso." in resguardo

        # Verificación de Pilares 1, 3, 4 y 5
        desglose = cr.desglose_score
        p1 = next(p for p in desglose if "Continuidad" in p.nombre)
        assert p1.puntaje_obtenido == 15
        assert "23 meses continuos declarados (2024-06 a 2026-04) sin lagunas tributarias" in p1.detalle

        p3 = next(p for p in desglose if "Holgura Débito/Crédito IVA (F29)" in p.nombre)
        assert p3 is not None
        assert p3.puntaje_obtenido == 20
        assert "Ratio Débito / Crédito Giro 12M: 1.45x" in p3.detalle

        p4 = next(p for p in desglose if "Rentabilidad" in p.nombre)
        assert p4.puntaje_obtenido == 13
        assert "RLI AT 2026: M$ 692.056 (9.1% s/ingresos; Utilidad Contable Cód. 1672: +M$ 656.065) | CPT: M$ 3.625.110 [Tope 13/15 pts: carpeta contiene solo 1 AT de F22, sin serie multianual verificable]" in p4.detalle

        p5 = next(p for p in desglose if "Cumplimiento Fiscal" in p.nombre)
        assert p5.puntaje_obtenido == 15
        assert "0 de 23 períodos F29 con recargos por mora fiscal (Cód. 94) y 0 postergaciones de IVA (Cód. 779)" in p5.detalle

        p6 = next(p for p in desglose if "Vigencia" in p.nombre)
        assert p6.puntaje_obtenido == 0
        assert "Carpeta tributaria vencida" in p6.detalle

    def test_generacion_pdf_nutrisa_layout(self, nutrisa_folder):
        """Genera el PDF y valida los textos clave de la versión v3.1.0."""
        pdf_bytes = PDFReport().generate(nutrisa_folder)
        assert len(pdf_bytes) > 10_000

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text_p1 = pdf.pages[0].extract_text()
            assert "(v3.1.0)" in text_p1
            assert "EMPRESA C S.A." in text_p1
            assert "96666666-8" in text_p1
            assert "NO EVALUABLE (Carpeta Vencida > 60 días)" in text_p1
            assert "n/d" in text_p1
            assert "Inicial: M$ 0" in text_p1
            assert "Máxima: M$ 0" in text_p1
            assert "Operación bloqueada" in text_p1
            assert "Se exige actualización" in text_p1
            assert "carpeta al mes en curso" in text_p1
            assert "Tope de concentración por proveedor: 3% CPT" in text_p1
            # Normalización de domicilio
            assert "01565 Bodeg" in text_p1
            # Aclaración de glosa Paso B2
            assert "(Proxy tributario sobre RLI/12; no equivale a flujo de caja libre)" in text_p1

            if len(pdf.pages) > 1:
                text_p2 = pdf.pages[1].extract_text()
                assert "Ingresos Giro Cód. 1657" in text_p2
                assert "RLI / Pérdida Cód. 1694/1695" in text_p2
                assert "Capital Propio CPT Cód. 645/1698" in text_p2
                assert "M$ 692.056 (Cód. 1694)" in text_p2
                assert "M$ 3.625.110" in text_p2
                assert "Motor Determinista Cavilaria v3.1.0" in text_p2
                # Base única de conciliación F22
                assert "3.2% s/base" in text_p2
                assert "F22 — CONCILIADO (<10% dif.)" in text_p2
                assert "s/base F29" not in text_p2

    def test_volcado_verificacion_nativa_nutrisa_pdfplumber(self, nutrisa_folder):
        """Verifica con asserts exactos los códigos F22 de la empresa."""
        assert len(nutrisa_folder.f22) >= 1
        f26 = nutrisa_folder.f22[0]
        assert f26.anio_tributario == "2026"
        assert f26.ingresos == 7_609_347_772
        assert f26.resultado_financiero == 656_064_546
        assert f26.renta_liquida_imponible == 692_055_540
        assert f26.capital_propio_tributario == 3_625_109_624
        assert f26.ppm in (84_066_318, 83_017_357)
        assert f26.saldo_liquidacion_anual == 103_837_639
        assert f26.ingresos_source_code == "1657"
        assert f26.rli_source_code == "1694"
        assert f26.cpt_source_code in ("645", "1698")
