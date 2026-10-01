from datetime import date
from decimal import Decimal
from pathlib import Path
import pytest

from src.core.tax_folder_engine import TaxFolderEngine
from src.credit.credit_risk_engine import CreditRiskEngine, _floor_tiered
from src.models.annual_tax_return import AnnualTaxReturn
from src.models.extract_result import ExtractResult, PageResult
from src.models.f29 import F29, F29Detail
from src.models.monthly_tax import MonthlyTax, MonthlyTaxResult
from src.models.section_result import SectionResult
from src.models.contributor import Contributor
from src.models.tax_folder import TaxFolder, Metadata
from src.parsers.f22_parser import F22Parser

NUTRISA_PDF = Path("/Users/josealfonsorossel/Downloads/Carpeta Tributaria Personalizada NUTRISA.pdf")


from src.services.monthly_tax_service import MonthlyTaxService


def _make_dummy_tax_folder(**kwargs) -> TaxFolder:
    if "metadata" not in kwargs:
        kwargs["metadata"] = Metadata(source_file="dummy.pdf", pages=1, processing_time=0.1)
    if "contributor" not in kwargs:
        kwargs["contributor"] = Contributor(rut="76123456-7", razon_social="EMPRESA PRUEBA SPA")
    if "monthly_analysis" not in kwargs and kwargs.get("monthly_taxes"):
        kwargs["monthly_analysis"] = MonthlyTaxService().analyze(kwargs["monthly_taxes"])
    return TaxFolder(**kwargs)


def _make_dummy_f29(periodo: str, ventas: int, compras: int, mora_c94: int = 0) -> F29:
    detalles = [
        F29Detail(codigo="563", glosa="Ventas Afectas", valor=str(ventas)),
        F29Detail(codigo="538", glosa="Débito Fiscal", valor=str(int(ventas * 0.19))),
        F29Detail(codigo="511", glosa="Crédito Fiscal", valor=str(int(compras * 0.19))),
        F29Detail(codigo="537", glosa="Total Crédito", valor=str(int(compras * 0.19))),
    ]
    if mora_c94 > 0:
        detalles.append(F29Detail(codigo="94", glosa="Total a pagar con recargo", valor=str(mora_c94)))
    return F29(
        periodo=periodo,
        folio="123456",
        fecha_presentacion="12/01/2026",
        detalles=detalles,
    )


def _make_dummy_monthly_tax(periodo: str, ventas: int, compras: int, exportacion: int = 0) -> MonthlyTax:
    tot_v = Decimal(ventas + exportacion)
    return MonthlyTax(
        periodo=periodo,
        ventas_afectas=Decimal(ventas),
        ventas_exentas=Decimal(0),
        ventas_exportacion=Decimal(exportacion),
        total_ventas=tot_v,
        compras=Decimal(compras),
        compras_operacionales=Decimal(compras),
        debito_fiscal=Decimal(int(ventas * 0.19)),
        credito_fiscal=Decimal(int(compras * 0.19)),
        credito_operacional=Decimal(int(compras * 0.19)),
    )


class TestV27ValidityArchetypes:
    """Suite de validación v2.7 de 8 arquetipos metodológicos."""

    # 1. Caso Dorado NUTRISA (95214000-0)
    @pytest.mark.skipif(
        not NUTRISA_PDF.exists() and not Path("tests/fixtures/cases/nutrisa.json").exists(),
        reason="PDF NUTRISA no disponible localmente",
    )
    def test_1_golden_nutrisa(self):
        fixture_json = Path("tests/fixtures/cases/nutrisa.json")
        if fixture_json.exists():
            folder = TaxFolder.model_validate_json(fixture_json.read_text(encoding="utf-8"))
            folder.credit_risk = CreditRiskEngine().calculate(folder, evaluation_date=date(2026, 6, 15))
        else:
            engine = TaxFolderEngine(str(NUTRISA_PDF))
            folder = engine.parse(evaluation_date=date(2026, 6, 15))
        cr = folder.credit_risk
        assert cr is not None
        assert cr.linea_maxima_condicionada == 14_400_000
        assert cr.linea_inicial_sugerida == 7_200_000
        assert cr.cupo_aprobado == 7_200_000
        assert cr.score_crediticio == 92
        assert cr.desempeno_tributario_texto == "Capacidad Operativa Tributaria Alta"
        assert cr.evaluacion_referencial == "ELEGIBLE PARA LÍNEA COMERCIAL (FASE 1 TRIBUTARIA) (Línea Sujeta a Dicom)"

        mem = cr.memoria_calculo
        assert mem["capital_propio_tributario"] == 3_625_109_624
        assert mem["freno_absorcion_operacional"] == 14_417_824

        corp = folder.corporate_info
        assert corp is not None
        assert len(corp.representantes) == 3
        assert corp.forma_actuacion_representantes == "En conjunto"

    # 2. Arquetipo Pérdida Tributaria (F22 con RLI <= 0 o Cód. 1695)
    def test_2_arquetipo_perdida_tributaria(self):
        meses = [f"2025{m:02d}" for m in range(1, 13)]
        f29_list = [_make_dummy_f29(p, 50_000_000, 30_000_000) for p in meses]
        mt_list = [_make_dummy_monthly_tax(p, 50_000_000, 30_000_000) for p in meses]
        f22_loss = AnnualTaxReturn(
            anio_tributario="2025",
            ingresos=600_000_000,
            renta_liquida_imponible=-50_000_000,
            perdidas=50_000_000,
            rli_source_code="1695",
            capital_propio_tributario=80_000_000,
            cpt_source_code="645",
        )
        folder = _make_dummy_tax_folder(
            f29=f29_list,
            monthly_taxes=mt_list,
            f22=[f22_loss],
        )
        engine = CreditRiskEngine()
        cr = engine.evaluate(folder)

        assert cr.linea_maxima_condicionada == 0
        assert cr.linea_inicial_sugerida == 0
        assert cr.cupo_aprobado == 0
        assert cr.memoria_calculo["freno_absorcion_operacional"] == 0
        assert "Pérdida Tributaria en F22" in cr.evaluacion_referencial
        assert "SIN LÍNEA AUTOMÁTICA" in cr.evaluacion_referencial

    # 3. Arquetipo Sin F22 (Empresa nueva, solo F29)
    def test_3_arquetipo_sin_f22_empresa_nueva(self):
        meses = [f"2025{m:02d}" for m in range(1, 9)]
        f29_list = [_make_dummy_f29(p, 60_000_000, 35_000_000) for p in meses]
        mt_list = [_make_dummy_monthly_tax(p, 60_000_000, 35_000_000) for p in meses]
        folder = _make_dummy_tax_folder(
            f29=f29_list,
            monthly_taxes=mt_list,
            f22=[],  # Sin F22
        )
        engine = CreditRiskEngine()
        cr = engine.evaluate(folder)

        # 8% Spread F29 con tope M$ 5.000
        assert cr.memoria_calculo["freno_absorcion_operacional"] <= 5_000_000
        assert cr.linea_maxima_condicionada <= 5_000_000
        assert "Acreditar última declaración F22 con RLI > 0" in cr.resguardo_comercial_sugerido

    # 4. Arquetipo Deterioro F29 Reciente (Caída 3M vs 12M de -25%)
    def test_4_arquetipo_deterioro_f29_reciente(self):
        meses = [f"2025{m:02d}" for m in range(1, 13)]
        f29_list = [_make_dummy_f29(p, 80_000_000, 40_000_000) for p in meses]
        mt_list = [_make_dummy_monthly_tax(p, 80_000_000, 40_000_000) for p in meses]
        f22 = AnnualTaxReturn(
            anio_tributario="2025",
            ingresos=960_000_000,
            renta_liquida_imponible=120_000_000,  # 10M / mes base
            capital_propio_tributario=500_000_000,
            rli_source_code="1694",
            cpt_source_code="645",
        )
        ma = MonthlyTaxResult(
            variacion_ventas_3m_pct=Decimal("-25.0"),
            promedio_ventas_12m=Decimal("80000000"),
            promedio_compras_operacionales_12m=Decimal("40000000"),
        )
        folder = _make_dummy_tax_folder(
            f29=f29_list,
            monthly_taxes=mt_list,
            f22=[f22],
            monthly_analysis=ma,
        )
        engine = CreditRiskEngine()
        cr = engine.evaluate(folder)

        # RLI mensualizada base = 10.000.000. Con factor 0.75x -> 7.500.000
        assert cr.memoria_calculo["rli_mensualizada_f22"] == 7_500_000

    # 5. Arquetipo Contracción Severa F29 (Caída 3M vs 12M de -45% sin recuperación YoY)
    def test_5_arquetipo_contraccion_severa_f29(self):
        meses = [f"2025{m:02d}" for m in range(1, 13)]
        f29_list = [_make_dummy_f29(p, 80_000_000, 40_000_000) for p in meses]
        mt_list = [_make_dummy_monthly_tax(p, 80_000_000, 40_000_000) for p in meses]
        f22 = AnnualTaxReturn(
            anio_tributario="2025",
            ingresos=960_000_000,
            renta_liquida_imponible=120_000_000,
            capital_propio_tributario=500_000_000,
        )
        ma = MonthlyTaxResult(
            variacion_ventas_3m_pct=Decimal("-45.0"),
            variacion_ventas_yoy_3m_pct=None,  # Sin recuperación YoY
            promedio_ventas_12m=Decimal("80000000"),
            promedio_compras_operacionales_12m=Decimal("40000000"),
        )
        folder = _make_dummy_tax_folder(
            f29=f29_list,
            monthly_taxes=mt_list,
            f22=[f22],
            monthly_analysis=ma,
        )
        engine = CreditRiskEngine()
        cr = engine.evaluate(folder)

        # Bloquea línea automática (Paso C = 0%, Línea = M$ 0)
        assert cr.linea_maxima_condicionada == 0
        assert cr.linea_inicial_sugerida == 0
        assert cr.cupo_aprobado == 0
        assert "Sin Línea Automática" in cr.evaluacion_referencial

    # 6. Arquetipo Empresa Exportadora (80% ventas exportación Cód. 020)
    def test_6_arquetipo_empresa_exportadora(self):
        meses = [f"2025{m:02d}" for m in range(1, 13)]
        f29_list = []
        mt_list = []
        for p in meses:
            # Ventas totales = 100M (80M exportación + 20M afectas)
            # Compras = 60M
            detalles = [
                F29Detail(codigo="020", glosa="Ventas Exportación", valor="80000000"),
                F29Detail(codigo="563", glosa="Ventas Afectas", valor="20000000"),
                F29Detail(codigo="538", glosa="Débito Fiscal", valor=str(int(20_000_000 * 0.19))),
                F29Detail(codigo="511", glosa="Crédito Fiscal", valor=str(int(60_000_000 * 0.19))),
                F29Detail(codigo="537", glosa="Total Crédito", valor=str(int(60_000_000 * 0.19))),
            ]
            f29_list.append(F29(periodo=p, folio="111", detalles=detalles))
            mt_list.append(_make_dummy_monthly_tax(p, 20_000_000, 60_000_000, exportacion=80_000_000))

        f22 = AnnualTaxReturn(
            anio_tributario="2025",
            ingresos=1_200_000_000,
            renta_liquida_imponible=150_000_000,
            capital_propio_tributario=400_000_000,
        )
        folder = _make_dummy_tax_folder(
            f29=f29_list,
            monthly_taxes=mt_list,
            f22=[f22],
        )
        engine = CreditRiskEngine()
        cr = engine.evaluate(folder)

        # Pilar 3 debe obtener puntaje completo (20 pts)
        p3 = next(p for p in cr.desglose_score if "Holgura" in p.nombre)
        assert p3.puntaje_obtenido == 20
        assert "Empresa exportadora: margen operacional holgado" in p3.detalle

    # 7. Arquetipo Micro-Empresa (_floor_tiered)
    def test_7_arquetipo_micro_empresa_floor_tiered(self):
        # Truncamiento escalonado
        assert _floor_tiered(84_000) == 80_000
        assert _floor_tiered(98_000) == 95_000
        assert _floor_tiered(345_000) == 340_000
        assert _floor_tiered(1_250_000) == 1_200_000
        assert _floor_tiered(8_500) == 0
        assert _floor_tiered(0) == 0
        assert _floor_tiered(None) == 0

    # 8. Arquetipo F22 Multigeneración (ProPyme Cód. 1440 y CPT 1696)
    def test_8_arquetipo_f22_multigeneracion(self):
        text = (
            "REPUBLICA DE CHILE AÑO TRIBUTARIO 2025 07N° 998877\n"
            "FORM. 22 IMPUESTOS ANUALES A LA RENTA\n"
            "1657 Ingresos del giro 180000000\n"
            "1440 Base Imponible Régimen ProPyme 35000000\n"
            "1696 Capital Propio Tributario Simplificado 90000000\n"
            "1113 Impuesto Primera Categoría 3500000\n"
            "36 PPM 2000000\n"
            "305 Saldo a pagar 1500000\n"
        )
        pages = [PageResult(page=1, text=text)]
        extract = ExtractResult(pages=pages)
        sections = SectionResult(secciones={"FORMULARIO 22": [1]})
        parser = F22Parser()
        result = parser.parse(extract, sections)

        assert len(result) == 1
        r = result[0]
        assert r.anio_tributario == "2025"
        assert r.ingresos == 180_000_000
        assert r.ingresos_source_code == "1657"
        assert r.renta_liquida_imponible == 35_000_000
        assert r.rli_source_code == "1440"
        assert r.capital_propio_tributario == 90_000_000
        assert r.cpt_source_code == "1696"
        assert r.idpc_determinado == 3_500_000
        assert r.ppm_imputados == 2_000_000
        assert r.saldo_liquidacion_anual == 1_500_000
        assert r.impuesto_determinado == 1_500_000
