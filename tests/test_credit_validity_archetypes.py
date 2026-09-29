from decimal import Decimal
from pathlib import Path
import pytest

from src.credit.credit_risk_engine import CreditRiskEngine, _floor_tiered
from src.credit.sector_benchmark import SectorBenchmark
from src.core.tax_folder_engine import TaxFolderEngine
from src.models.annual_tax_return import AnnualTaxReturn
from src.models.contributor import Contributor
from src.models.f29 import F29, F29Detail
from src.models.monthly_tax import MonthlyTax, MonthlyTaxResult
from src.models.tax_folder import Metadata, TaxFolder

NUTRISA_PDF = Path("/Users/josealfonsorossel/Downloads/Carpeta Tributaria Personalizada NUTRISA.pdf")


def _f29(periodo: str, **codigos: str) -> F29:
    detalles = [F29Detail(codigo=c, glosa=c, valor=v) for c, v in codigos.items()]
    return F29(periodo=periodo, folio=f"f{periodo}", detalles=detalles)


def _build_tax_folder(
    f29_list: list[F29] | None = None,
    f22_list: list[AnnualTaxReturn] | None = None,
    monthly_taxes: list[MonthlyTax] | None = None,
    monthly_analysis: MonthlyTaxResult | None = None,
) -> TaxFolder:
    f29_list = f29_list or []
    if monthly_taxes is None and f29_list:
        monthly_taxes = [
            MonthlyTax(
                periodo=f.periodo,
                total_ventas=Decimal(10_000_000),
                ventas_afectas=Decimal(10_000_000),
                compras=Decimal(6_000_000),
                compras_operacionales=Decimal(6_000_000),
                debito_fiscal=Decimal(1_900_000),
                credito_fiscal=Decimal(1_140_000),
            )
            for f in f29_list
        ]
    return TaxFolder(
        contributor=Contributor(rut="77123456-7", razon_social="ARQUETIPO TEST SpA"),
        f29=f29_list,
        f22=f22_list or [],
        monthly_taxes=monthly_taxes or [],
        monthly_analysis=monthly_analysis,
        metadata=Metadata(source_file="test_archetype.pdf", pages=1, processing_time=0.0),
    )


class TestCreditValidityArchetypes:
    """Suite de validación de los 6 arquetipos de riesgo crediticio determinista v2.7."""

    @pytest.mark.skipif(not NUTRISA_PDF.exists(), reason="PDF de prueba NUTRISA no disponible en entorno local")
    def test_archetype_1_manufactura_14a_sana_nutrisa(self):
        """Arquetipo 1: Manufactura 14A sana (NUTRISA Golden Fixture).

        Línea Máxima M$ 14.400, Inicial M$ 7.200, Score 92.
        """
        engine = TaxFolderEngine(str(NUTRISA_PDF))
        tf = engine.parse()
        cr = tf.credit_risk

        assert cr is not None
        assert cr.score_crediticio == 92
        assert cr.evaluacion_referencial == "ELEGIBLE PARA LÍNEA COMERCIAL (FASE 1 TRIBUTARIA) (Línea Sujeta a Dicom)"
        assert cr.linea_maxima_condicionada == 14_400_000
        assert cr.linea_inicial_sugerida == 7_200_000
        assert cr.memoria_calculo["freno_absorcion_operacional"] == 14_417_824

    def test_archetype_2_empresa_con_perdida_tributaria_f22(self):
        """Arquetipo 2: Empresa con Pérdida Tributaria en F22 (RLI <= 0).

        Verifica que Paso B2 == 0, Línea Máxima == 0, Línea Inicial == 0 y
        dictamen 'SIN LÍNEA AUTOMÁTICA (Pérdida Tributaria en F22 — Requiere Evaluación Manual con EE.FF.)'.
        """
        f29_list = [_f29(f"2025-{m:02d}", **{"563": "10000000", "511": "6000000"}) for m in range(1, 13)]
        # F22 declara pérdida tributaria (RLI = -5.000.000, pérdidas = 5.000.000)
        f22_loss = AnnualTaxReturn(
            anio_tributario="2025",
            renta_liquida_imponible=-5_000_000,
            perdidas=5_000_000,
            capital_propio_tributario=50_000_000,
            ingresos=120_000_000,
        )
        tf = _build_tax_folder(f29_list=f29_list, f22_list=[f22_loss])
        result = CreditRiskEngine().evaluate(tf)

        assert result.memoria_calculo["freno_absorcion_operacional"] == 0
        assert result.linea_maxima_condicionada == 0
        assert result.linea_inicial_sugerida == 0
        assert result.cupo_aprobado == 0
        assert result.decision.resultado_base == "RECHAZADO"
        assert result.evaluacion_referencial == "SIN LÍNEA AUTOMÁTICA (Pérdida Tributaria en F22 — Evaluación Manual con EE.FF.)"

    def test_archetype_3_carpeta_sin_f22_con_12m_f29_sanos(self):
        """Arquetipo 3: Carpeta sin F22 pero con 12M F29 sanos.

        Verifica que aplique fallback de 8% del Spread F29 con condición suspensiva de presentar F22.
        """
        f29_list = [_f29(f"2025-{m:02d}", **{"563": "10000000", "511": "4000000"}) for m in range(1, 13)]
        # No se incluye F22 en la carpeta
        tf = _build_tax_folder(f29_list=f29_list, f22_list=[])
        result = CreditRiskEngine().evaluate(tf)

        # Spread = 10.000.000 - 6.000.000 = 4.000.000.
        # Fallback B2 = min(8% * 4.000.000, 5.000.000) = min(320.000, 5.000.000) = 320.000.
        assert result.memoria_calculo["ausencia_f22"] is True
        assert result.memoria_calculo["rli_fallback_8pct"] is True
        assert result.memoria_calculo["freno_absorcion_operacional"] == 320_000

        # Condición suspensiva obligatoria
        condicion_esperada = "Condición suspensiva: Acreditar última declaración F22 con RLI > 0 para liberar línea superior a M$ 5.000."
        assert condicion_esperada in result.decision.protocolo_operativo or condicion_esperada in result.decision.resguardo_comercial_sugerido

    def test_archetype_4_deterioro_reciente_severo_f29(self):
        """Arquetipo 4: Deterioro reciente severo.

        RLI positiva en año anterior pero caída de -25% en ventas 3M vs 12M F29.
        Verifica que B2 castigue la RLI mensualizada en un 25% (factor 0.75x).
        """
        f29_list = [_f29(f"2025-{m:02d}", **{"563": "10000000", "511": "4000000"}) for m in range(1, 13)]
        # RLI anual = 24.000.000 -> Base mensual = 2.000.000.
        # Con 25% de RLI base = 500.000.
        f22 = AnnualTaxReturn(
            anio_tributario="2025",
            renta_liquida_imponible=24_000_000,
            capital_propio_tributario=100_000_000,
            ingresos=120_000_000,
        )
        # Caída del 25% en ventas trimestrales (-25.0%)
        analysis = MonthlyTaxResult(variacion_ventas_3m_pct=Decimal("-25.0"))
        tf = _build_tax_folder(f29_list=f29_list, f22_list=[f22], monthly_analysis=analysis)

        result = CreditRiskEngine().evaluate(tf)

        # RLI base mensual = 2.000.000.
        # Factor deterioro = 1.0 + (-0.25) = 0.75.
        # RLI mensualizada ajustada = 2.000.000 * 0.75 = 1.500.000.
        # Freno B2 = min(15% * Spread [900.000], 25% * 1.500.000 [375.000]) = 375.000.
        assert result.memoria_calculo["rli_mensualizada_f22"] == 1_500_000
        assert result.memoria_calculo["freno_absorcion_operacional"] == 375_000

    def test_archetype_5_proteccion_exportador_pilar_3(self):
        """Arquetipo 5: Exportadora con >30% de ventas en Cód. 020 y Débito/Crédito < 1.0x.

        Verifica que no sea penalizada artificialmente en el Pilar 3.
        """
        f29_list = []
        monthly_taxes = []
        for m in range(1, 13):
            p = f"2025-{m:02d}"
            # Venta neta = 10M (6M afectas + 4M exportación = 40% exportación)
            # Débito fiscal = 19% de 6M = 1.14M
            # Crédito fiscal = 1.33M (Ratio Débito/Crédito = 0.85x < 1.0x)
            # Sin protección exportador recibiría 5 pts en Pilar 3.
            # Ventas/Compras = 10M / 7M = 1.43x > 1.25x -> Con protección recibe 20 pts.
            f29_list.append(_f29(p, **{"020": "4000000", "563": "6000000", "511": "7000000", "538": "1140000", "537": "1330000"}))
            monthly_taxes.append(
                MonthlyTax(
                    periodo=p,
                    total_ventas=Decimal(10_000_000),
                    ventas_afectas=Decimal(6_000_000),
                    ventas_exportacion=Decimal(4_000_000),
                    compras=Decimal(7_000_000),
                    compras_operacionales=Decimal(7_000_000),
                    debito_fiscal=Decimal(1_140_000),
                    credito_fiscal=Decimal(1_330_000),
                )
            )

        f22 = AnnualTaxReturn(
            anio_tributario="2025",
            renta_liquida_imponible=20_000_000,
            capital_propio_tributario=80_000_000,
            ingresos=120_000_000,
        )
        tf = _build_tax_folder(f29_list=f29_list, f22_list=[f22], monthly_taxes=monthly_taxes)
        result = CreditRiskEngine().evaluate(tf)

        p3 = next(p for p in result.desglose_score if "Holgura Débito/Crédito" in p.nombre)
        # Debe obtener puntaje no castigado (>= 17 pts, específicamente 20 pts por Ventas/Compras > 1.25x)
        assert p3.puntaje_obtenido >= 17
        assert "exportadora" in p3.detalle.lower()

    def test_archetype_6_microempresa_tiered_floor(self):
        """Arquetipo 6: Micro-empresa con línea técnica escalonada.

        Verifica truncado a M$ 340 (múltiplo de M$ 10) y soporte de tramo $10k-$100k (múltiplos de $5k).
        """
        assert _floor_tiered(345_000) == 340_000
        assert _floor_tiered(995_000) == 990_000
        assert _floor_tiered(14_417_824) == 14_400_000
        assert _floor_tiered(84_000) == 80_000
        assert _floor_tiered(99_000) == 95_000
        assert _floor_tiered(9_000) == 0
