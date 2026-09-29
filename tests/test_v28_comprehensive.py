import decimal
from decimal import Decimal
import pytest

from src.models.annual_tax_return import AnnualTaxReturn
from src.models.monthly_tax import MonthlyTax
from src.models.tax_folder import TaxFolder
from src.parsers.f22_parser import F22Parser
from src.credit.credit_risk_engine import CreditRiskEngine, _floor_tiered
from src.models.credit_risk import CalidadDatos, Hechos, Indicadores, MoraEfectiva, MargenVsGiro, RespaldoEstructural


class TestV28Comprehensive:
    def test_pyme_14d3_parsing(self):
        """Verifica que F22Parser extraiga correctamente los códigos del régimen 14D N°3 (Pro Pyme General):
        Recuadro 17: Cód. 1400 (Ingresos), Cód. 1440 (Base Imponible/RLI).
        Recuadro 19: Cód. 1545 (CPT simplificado).
        """
        parser = F22Parser()
        raw_text = """
        AÑO TRIBUTARIO 2026
        RECUADRO N° 17: BASE IMPONIBLE RÉGIMEN PRO PYME
        1400 Total ingresos percibidos del giro 850.000.000
        1440 Base imponible afecta a IDPC 95.000.000
        RECUADRO N° 19: CAPITAL PROPIO TRIBUTARIO SIMPLIFICADO
        1545 Capital Propio Tributario positivo final 320.000.000
        """
        declaracion = parser._extraer_datos(raw_text, "2026")
        assert declaracion.anio_tributario == "2026"
        assert declaracion.ingresos == 850_000_000
        assert declaracion.ingresos_source_code == "1400"
        assert declaracion.renta_liquida_imponible == 95_000_000
        assert declaracion.rli_source_code == "1440"
        assert declaracion.capital_propio_tributario == 320_000_000
        assert declaracion.cpt_source_code == "1545"

    def test_pyme_14d3_perdida(self):
        """Verifica que cuando una 14D3 registre pérdida en Cód. 1450, se asigne RLI negativa."""
        parser = F22Parser()
        raw_text = """
        AÑO TRIBUTARIO 2026
        1400 Total ingresos percibidos del giro 500.000.000
        1450 Pérdida tributaria del ejercicio 45.000.000
        1546 Capital Propio Tributario negativo final 10.000.000
        """
        declaracion = parser._extraer_datos(raw_text, "2026")
        assert declaracion.renta_liquida_imponible == -45_000_000
        assert declaracion.rli_source_code == "1450"
        assert declaracion.capital_propio_tributario == -10_000_000
        assert declaracion.cpt_source_code == "1546"

    def test_sin_f22_fallback_f29(self):
        """Verifica que una carpeta sin declaraciones F22 opere bajo fallback F29 (8% C_base)
        y aplique condición suspensiva de acreditación de F22.
        """
        engine = CreditRiskEngine()
        taxes = []
        for i in range(1, 13):
            taxes.append(
                MonthlyTax(
                    periodo=f"2025-{i:02d}",
                    total_ventas=Decimal("50000000"),
                    compras=Decimal("35000000"),
                    compras_operacionales=Decimal("35000000"),
                    debito_fiscal=Decimal("9500000"),
                    credito_fiscal=Decimal("6650000"),
                    iva_determinado=Decimal("2850000"),
                )
            )
        from src.models.contributor import Contributor
        from src.models.tax_folder import Metadata
        from src.models.f29 import F29, F29Detail

        f29_list = []
        for i in range(1, 13):
            periodo = f"2025-{i:02d}"
            f29_list.append(
                F29(
                    periodo=periodo,
                    folio=f"f{periodo}",
                    detalles=[
                        F29Detail(codigo="538", glosa="ventas", valor="50000000"),
                        F29Detail(codigo="511", glosa="compras", valor="35000000"),
                        F29Detail(codigo="537", glosa="credito", valor="6650000"),
                    ],
                )
            )

        tf = TaxFolder(
            contributor=Contributor(razon_social="PYME SERVICIOS SIN F22"),
            monthly_taxes=taxes,
            f29=f29_list,
            f22=[],
            metadata=Metadata(source_file="test_sin_f22.pdf", pages=12, processing_time=0.1),
        )
        res = engine.evaluate(tf)

        assert res.score_compuesto is not None
        mem = res.decision.memoria_calculo
        assert mem.get("ausencia_f22") is True
        assert res.linea_maxima_sugerida > 0
        assert "Condición suspensiva: Acreditar última declaración F22" in res.decision.protocolo_operativo

    def test_tramos_conductuales_score_75_84_y_65_74(self):
        """Verifica los factores de ajuste y aperturas para los tramos 75-84 (80% / 40%)
        y 65-74 (60% / 30%).
        """
        engine = CreditRiskEngine()
        # Verificar tramo 75-84
        memoria_75 = {
            "cupo_maximo_sugerido": 20_000_000,
            "techo_operativo_8pct": 20_000_000,
            "rli_declarada_le_zero": False,
            "ausencia_f22": False,
            "factor_riesgo_phi": 1.0,
            "castigos_aplicados": [],
        }
        dec_75 = engine._decidir(
            hechos=Hechos(),
            indicadores=Indicadores(
                mora_efectiva=MoraEfectiva(score=90, meses_con_recargo=0),
                margen_vs_giro=MargenVsGiro(score=80),
                respaldo_estructural=RespaldoEstructural(score=80),
            ),
            score_compuesto=78,
            cupo_solicitado=None,
            cupo_maximo=20_000_000,
            memoria=memoria_75,
            aval_obligatorio=False,
        )
        assert dec_75.clasificacion_riesgo == "PERFIL TRIBUTARIO MODERADO"
        assert dec_75.linea_maxima_sugerida == _floor_tiered(20_000_000 * 0.80)
        assert dec_75.linea_inicial_sugerida == _floor_tiered(dec_75.linea_maxima_sugerida * 0.40)
        assert dec_75.memoria_calculo["factor_ajuste_conductual_pct"] == 80
        assert dec_75.memoria_calculo["pct_apertura"] == 40

        # Verificar tramo 65-74
        memoria_65 = {
            "cupo_maximo_sugerido": 20_000_000,
            "techo_operativo_8pct": 20_000_000,
            "rli_declarada_le_zero": False,
            "ausencia_f22": False,
            "factor_riesgo_phi": 1.0,
            "castigos_aplicados": [],
        }
        dec_65 = engine._decidir(
            hechos=Hechos(),
            indicadores=Indicadores(
                mora_efectiva=MoraEfectiva(score=70, meses_con_recargo=0),
                margen_vs_giro=MargenVsGiro(score=70),
                respaldo_estructural=RespaldoEstructural(score=70),
            ),
            score_compuesto=68,
            cupo_solicitado=None,
            cupo_maximo=20_000_000,
            memoria=memoria_65,
            aval_obligatorio=False,
        )
        assert dec_65.clasificacion_riesgo == "PERFIL TRIBUTARIO ACOTADO"
        assert dec_65.linea_maxima_sugerida == _floor_tiered(20_000_000 * 0.60)
        assert dec_65.linea_inicial_sugerida == _floor_tiered(dec_65.linea_maxima_sugerida * 0.30)
        assert dec_65.memoria_calculo["factor_ajuste_conductual_pct"] == 60
        assert dec_65.memoria_calculo["pct_apertura"] == 30
