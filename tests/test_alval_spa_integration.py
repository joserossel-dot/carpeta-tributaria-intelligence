from pathlib import Path
import pytest

from src.models.tax_folder import TaxFolder
from src.credit.credit_risk_engine import CreditRiskEngine

ALVAL_FIXTURE = Path(__file__).parent / "fixtures" / "cases" / "alval_spa.json"


class TestAlvalSpaIntegration:
    @pytest.fixture(scope="class")
    def alval_folder(self):
        folder = TaxFolder.model_validate_json(ALVAL_FIXTURE.read_text(encoding="utf-8"))
        folder.credit_risk = CreditRiskEngine().calculate(folder)
        return folder

    def test_contributor_info(self, alval_folder):
        """Verifica la extracción limpia del contribuyente, domicilio y comuna/región."""
        contrib = alval_folder.contributor
        assert contrib is not None
        assert contrib.rut == "77777777-7"
        assert contrib.razon_social == "EMPRESA A SPA"
        assert contrib.comuna == "PUDAHUEL"
        assert contrib.region == "METROPOLITANA DE SANTIAGO"
        assert "null" not in (contrib.domicilio or "").lower()
        assert contrib.domicilio == "CAMINO RENCA LAMPA 9100 LT.10 a, PUDAHUEL"

    def test_representantes_sin_accionistas(self, alval_folder):
        """Verifica que se capturen los 2 representantes multilínea con actuación 'Cualquiera' y no a los accionistas."""
        corp = alval_folder.corporate_info
        assert corp is not None
        assert corp.forma_actuacion_representantes == "Cualquiera"

        reps = corp.representantes
        assert len(reps) == 2

        nombres = [r.nombre for r in reps]
        assert "REPRESENTANTE 1" in nombres
        assert "REPRESENTANTE 2" in nombres
        # Verificación estricta de que no se mezclaron accionistas
        assert not any("SOCIO" in n for n in nombres)

        ruts = {r.nombre: r.rut for r in reps}
        assert ruts["REPRESENTANTE 1"] == "11111111-1"
        assert ruts["REPRESENTANTE 2"] == "22222222-2"

        for r in reps:
            assert r.forma_actuacion == "Cualquiera"
            assert r.vigente is True

    def test_f22_multigeneracion_y_perdida(self, alval_folder):
        """Verifica los 3 años F22 con pérdida tributaria negativa en AT 2026 y saldo 305 negativo."""
        assert len(alval_folder.f22) == 3

        f22_by_ano = {f.anio_tributario: f for f in alval_folder.f22}
        assert "2026" in f22_by_ano
        assert "2025" in f22_by_ano
        assert "2024" in f22_by_ano

        # AT 2026
        f26 = f22_by_ano["2026"]
        assert f26.ingresos == 7121034432
        assert f26.ingresos_source_code == "1657"
        assert f26.renta_liquida_imponible == -31382439
        assert f26.rli_source_code == "1695"
        assert f26.resultado_financiero == 103376031
        assert f26.capital_propio_tributario == 1756914649
        assert f26.cpt_source_code in ("1698", "645")
        assert f26.saldo_liquidacion_anual == -24086464

        # AT 2025
        f25 = f22_by_ano["2025"]
        assert f25.ingresos == 5850948753
        assert f25.ingresos_source_code == "1657"
        assert f25.renta_liquida_imponible == 13525934
        assert f25.rli_source_code == "1694"
        assert f25.resultado_financiero == 70651986
        assert f25.capital_propio_tributario == 1716248257
        assert f25.cpt_source_code in ("1698", "645")

        # AT 2024
        f24 = f22_by_ano["2024"]
        assert f24.ingresos == 5112917380
        assert f24.ingresos_source_code == "1657"
        assert f24.renta_liquida_imponible == 230291714
        assert f24.rli_source_code == "1694"
        assert f24.resultado_financiero == 176661212
        assert f24.capital_propio_tributario == 568044045
        assert f24.cpt_source_code in ("1698", "645")

    def test_f29_continuity(self, alval_folder):
        """Verifica que se procesen los 36 meses continuos de F29."""
        assert len(alval_folder.monthly_taxes) == 36

    def test_regla_comite_rechazo_perdida(self, alval_folder):
        """Verifica la regla estricta de comité: pérdida tributaria genera Línea = 0 y veredicto explicativo."""
        cr = alval_folder.credit_risk
        assert cr is not None
        # En v3.0.0+, carpeta emitida 27/07/2026 tiene > 60 días al 01/10/2026, por lo que Pilar 6 = 0 pts (62 pts -> Baja)
        assert cr.score_compuesto == 62
        assert cr.decision.desempeno_tributario_texto == "Capacidad Operativa Tributaria Baja"
        assert cr.linea_maxima_sugerida == 0
        assert cr.linea_inicial_sugerida == 0
        assert cr.veredicto == "NO EVALUABLE (Carpeta Vencida > 60 días)"

        mem = cr.decision.memoria_calculo
        assert mem["rli_declarada_le_zero"] is True
        assert mem["freno_absorcion_operacional"] == 0.0
        assert mem["linea_maxima_condicionada"] == 0

    def test_volcado_verificacion_nativa_pdfplumber(self, alval_folder):
        """Verifica con asserts exactos los 12 códigos F22 de la empresa."""
        f22_by_ano = {f.anio_tributario: f for f in alval_folder.f22}
        assert f22_by_ano["2026"].ingresos == 7_121_034_432
        assert f22_by_ano["2026"].resultado_financiero == 103_376_031
        assert f22_by_ano["2026"].renta_liquida_imponible == -31_382_439
        assert f22_by_ano["2026"].perdidas == 31_382_439
        assert f22_by_ano["2026"].capital_propio_tributario == 1_756_914_649
        assert f22_by_ano["2026"].ppm == 25_456_103
        assert f22_by_ano["2026"].saldo_liquidacion_anual == -24_086_464

        assert f22_by_ano["2025"].ingresos == 5_850_948_753
        assert f22_by_ano["2025"].resultado_financiero in (70_651_986, 70_651_980)
        assert f22_by_ano["2025"].renta_liquida_imponible == 13_525_934
        assert f22_by_ano["2025"].capital_propio_tributario == 1_716_248_257

        assert f22_by_ano["2024"].ingresos == 5_112_917_380
        assert f22_by_ano["2024"].resultado_financiero == 176_661_212
        assert f22_by_ano["2024"].renta_liquida_imponible == 230_291_714
        assert f22_by_ano["2024"].capital_propio_tributario == 568_044_045

    def test_generacion_pdf_alval_spa_layout(self, alval_folder):
        """Genera el PDF y valida los textos clave, códigos F22 y glosas de la versión v3.1.0."""
        import io
        import pdfplumber
        from src.reports.pdf_report import PDFReport

        pdf_bytes = PDFReport().generate(alval_folder)
        assert len(pdf_bytes) > 10_000

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            assert len(pdf.pages) == 2
            text_p1 = pdf.pages[0].extract_text()
            text_p1_clean = " ".join(text_p1.split())
            assert "(v3.1.0)" in text_p1_clean
            assert "EMPRESA A SPA" in text_p1_clean
            assert "77777777-7" in text_p1_clean
            assert "NO EVALUABLE (Carpeta Vencida > 60 días)" in text_p1_clean
            assert "n/d" in text_p1_clean
            assert "Operación bloqueada" in text_p1_clean
            assert "Se exige actualización" in text_p1_clean
            assert "carpeta al mes en curso" in text_p1_clean
            assert "Pérdida Tributaria en último F22" in text_p1_clean
            assert "2 representante(s) registrado(s)" in text_p1_clean
            assert "Cualquiera" in text_p1_clean
            assert "CAMINO RENCA LAMPA 9100 LT.10 a, PUDAHUEL" in text_p1_clean
            assert "+11.0%" in text_p1_clean
            assert "alta volatilidad mensual" in text_p1_clean
            assert "CV: 24.1%" in text_p1_clean
            assert "Rango:" in text_p1_clean
            assert "M$ 402.100 a M$ 911.478" in text_p1_clean
            assert "Margen operacional ajustado" in text_p1_clean
            assert "Ratio Débito / Crédito Giro 12M: 1.11x" in text_p1_clean
            assert "Compras Giro: 1.07x" in text_p1_clean
            assert "RLI AT 2026: -M$ 31.382" in text_p1_clean
            assert "Utilidad Contable s/Balance Cód. 1672" in text_p1_clean
            assert "+M$ 103.376" in text_p1_clean
            assert "CPT: M$ 1.756.915" in text_p1_clean
            assert "Respaldo patrimonial mitigado por pérdida" in text_p1_clean
            assert "0 de 36 períodos con mora Cód. 94" in text_p1_clean
            assert "5 de últ. 12M sin IVA a pagar" in text_p1_clean

            text_p2 = pdf.pages[1].extract_text()
            full_text = " ".join(text_p1.split()) + " " + " ".join(text_p2.split())
            assert "Alerta de Overtrading y Deterioro Multianual de Margen" in full_text
            assert "compras superan a las ventas en 6" in full_text
            assert "Variación positiva de CPT" in full_text
            assert "verificación en EERR" in full_text
            assert "Ingresos Giro Cód. 1657" in text_p2
            assert "RLI / Pérdida Cód. 1694/1695" in text_p2
            assert "Capital Propio CPT Cód. 645/1698" in text_p2
            assert "-M$ 31.382 (Cód. 1695)" in text_p2
            assert "M$ 13.526 (Cód. 1694)" in text_p2
            assert "M$ 230.292 (Cód. 1694)" in text_p2
            assert "M$ 1.756.915" in text_p2
            assert "M$ 1.716.248" in text_p2
            assert "M$ 568.044" in text_p2
            assert "2025-07 M$ 911.478 M$ 971.150 M$ 173.181" in text_p2
            assert "1.4% s/base" in text_p2
            assert "F22 — CONCILIADO (<10% dif.)" in text_p2
            assert "s/base F29" not in text_p2
            assert "CONCILIADO (<10% dif.)" in text_p2
            assert "Motor Determinista Cavilaria v3.1.0" in text_p2
