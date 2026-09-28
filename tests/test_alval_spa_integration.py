from pathlib import Path
import pytest

from src.core.tax_folder_engine import TaxFolderEngine

ALVAL_PDF = Path("/Users/josealfonsorossel/Downloads/Carpeta_Tributaria_Regular (8).pdf")


@pytest.mark.skipif(not ALVAL_PDF.exists(), reason="PDF de prueba ALVAL SPA no disponible en entorno local")
class TestAlvalSpaIntegration:
    @pytest.fixture(scope="class")
    def alval_folder(self):
        engine = TaxFolderEngine(str(ALVAL_PDF))
        return engine.parse()

    def test_contributor_info(self, alval_folder):
        """Verifica la extracción limpia del contribuyente, domicilio y comuna/región."""
        contrib = alval_folder.contributor
        assert contrib is not None
        assert contrib.rut == "76293939-8"
        assert contrib.razon_social == "ALVAL SPA"
        assert contrib.comuna == "PUDAHUEL"
        assert contrib.region == "METROPOLITANA DE SANTIAGO"
        assert "null" not in (contrib.domicilio or "").lower()
        assert contrib.domicilio == "CAMINO RENCA LAMPA 9100 LT.10 a, PUDAHUEL"

    def test_representantes_sin_accionistas(self, alval_folder):
        """Verifica que se capturen los 2 representantes multilínea con actuación 'Cualquiera' y no a los accionistas DAB SPA / AG SPA."""
        corp = alval_folder.corporate_info
        assert corp is not None
        assert corp.forma_actuacion_representantes == "Cualquiera"

        reps = corp.representantes
        assert len(reps) == 2

        nombres = [r.nombre for r in reps]
        assert "IGNACIO JOSE ALLENDES CORREA" in nombres
        assert "DIEGO JOSE VALENZUELA INFANTE" in nombres
        # Verificación estricta de que no se mezclaron accionistas
        assert not any("DAB SPA" in n or "AG SPA" in n for n in nombres)

        ruts = {r.nombre: r.rut for r in reps}
        assert ruts["IGNACIO JOSE ALLENDES CORREA"] == "16369817-K"
        assert ruts["DIEGO JOSE VALENZUELA INFANTE"] == "16371206-7"

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
        assert f26.cpt_source_code == "645"
        assert f26.saldo_liquidacion_anual == -24086464

        # AT 2025
        f25 = f22_by_ano["2025"]
        assert f25.ingresos == 5850948753
        assert f25.ingresos_source_code == "1657"
        assert f25.renta_liquida_imponible == 13525934
        assert f25.rli_source_code == "1694"
        assert f25.resultado_financiero == 70651986
        assert f25.capital_propio_tributario == 1716248257
        assert f25.cpt_source_code == "645"

        # AT 2024
        f24 = f22_by_ano["2024"]
        assert f24.ingresos == 5112917380
        assert f24.ingresos_source_code == "1657"
        assert f24.renta_liquida_imponible == 230291714
        assert f24.rli_source_code == "1694"
        assert f24.resultado_financiero == 176661212
        assert f24.capital_propio_tributario == 568044045
        assert f24.cpt_source_code == "645"

    def test_f29_continuity(self, alval_folder):
        """Verifica que se procesen los 36 meses continuos de F29."""
        assert len(alval_folder.monthly_taxes) == 36

    def test_regla_comite_rechazo_perdida(self, alval_folder):
        """Verifica la regla estricta de comité: pérdida tributaria genera Línea = 0 y veredicto explicativo."""
        cr = alval_folder.credit_risk
        assert cr is not None
        assert cr.score_compuesto == 85
        assert cr.linea_maxima_sugerida == 0
        assert cr.linea_inicial_sugerida == 0
        assert cr.veredicto == "SIN LÍNEA AUTOMÁTICA (Pérdida Tributaria en F22 — Evaluación Manual con EE.FF.)"

        mem = cr.decision.memoria_calculo
        assert mem["rli_declarada_le_zero"] is True
        assert mem["freno_absorcion_operacional"] == 0.0
        assert mem["linea_maxima_condicionada"] == 0
