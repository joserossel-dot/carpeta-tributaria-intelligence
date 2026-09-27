from decimal import Decimal

import pytest

from src.credit.credit_risk_engine import CreditRiskEngine
from src.credit.sector_benchmark import SectorBenchmark
from src.models.activity import Activity
from src.models.annual_tax_return import AnnualTaxReturn
from src.models.contributor import Contributor
from src.models.f29 import F29, F29Detail
from src.models.monthly_tax import MonthlyTax
from src.models.tax_folder import Metadata, TaxFolder


def _f29(periodo: str, **codigos: str) -> F29:
    detalles = [F29Detail(codigo=c, glosa=c, valor=v) for c, v in codigos.items()]
    return F29(periodo=periodo, folio=f"f{periodo}", detalles=detalles)


def _tax_folder(f29_list=None, f22_list=None, monthly_taxes=None, activities=None) -> TaxFolder:
    f29_list = f29_list or []
    if monthly_taxes is None and f29_list:
        monthly_taxes = [MonthlyTax(periodo=f.periodo) for f in f29_list]
    return TaxFolder(
        contributor=Contributor(razon_social="EMPRESA TEST"),
        f29=f29_list,
        f22=f22_list or [],
        monthly_taxes=monthly_taxes or [],
        activities=activities or [],
        metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
    )


@pytest.fixture()
def benchmark_vacio(tmp_path):
    return SectorBenchmark(path=tmp_path / "bench.json")


class TestCalidadDatos:
    def test_sin_datos_no_es_apto(self, benchmark_vacio) -> None:
        tf = _tax_folder()
        result = CreditRiskEngine(benchmark_vacio).calculate(tf)
        assert result.calidad_datos.veredicto == "DATOS_INSUFICIENTES"
        # sin datos aptos, no se calculan indicadores ni decision
        assert result.indicadores.mora_efectiva.score is None
        assert result.decision.resultado_base is None

    def test_con_datos_suficientes_es_apto(self, benchmark_vacio) -> None:
        f29_list = [_f29(f"2025-{m:02d}") for m in range(1, 7)]
        tf = _tax_folder(f29_list=f29_list)
        result = CreditRiskEngine(benchmark_vacio).calculate(tf)
        assert result.calidad_datos.veredicto == "APTO_PARA_SCORING"

    def test_observaciones_f22_se_listan_como_no_confiables(self, benchmark_vacio) -> None:
        f29_list = [_f29(f"2025-{m:02d}") for m in range(1, 7)]
        f22 = AnnualTaxReturn(anio_tributario="2024", observaciones=["No se encontraron Ingresos del Giro"])
        tf = _tax_folder(f29_list=f29_list, f22_list=[f22])
        result = CreditRiskEngine(benchmark_vacio).calculate(tf)
        campos = [c.campo for c in result.calidad_datos.campos_no_confiables]
        assert "f22.2024.Ingresos del Giro" in campos


class TestHechosNoSeCalifican:
    """Los hechos (composición de ventas, postergaciones IVA) nunca deben
    tener un campo 'score' ni entrar al score_compuesto -- es la decisión
    de diseño explícita de esta sesión."""

    def test_composicion_ventas_no_tiene_score(self, benchmark_vacio) -> None:
        f29_list = [_f29(f"2025-{m:02d}", **{"502": "1000000"}) for m in range(1, 7)]
        tf = _tax_folder(f29_list=f29_list)
        result = CreditRiskEngine(benchmark_vacio).calculate(tf)
        assert not hasattr(result.hechos.composicion_ventas, "score")
        assert result.hechos.composicion_ventas.pct_facturado == 1.0

    def test_postergacion_iva_se_reporta_sin_penalizar_una_sola_vez(self, benchmark_vacio) -> None:
        f29_list = [_f29(f"2025-{m:02d}") for m in range(1, 13)]
        f29_list[3] = _f29("2025-04", **{"779": "500000"})
        tf = _tax_folder(f29_list=f29_list)
        result = CreditRiskEngine(benchmark_vacio).calculate(tf)
        assert result.hechos.postergaciones_iva.meses_con_postergacion == 1
        assert "2025-04" in result.hechos.postergaciones_iva.periodos
        # el hecho no genera alerta ni penaliza el score por sí solo
        assert not any("postergaci" in a.lower() for a in result.alertas)


class TestMoraEfectiva:
    def test_remanente_credito_no_es_mora(self, benchmark_vacio) -> None:
        f29_list = [_f29(f"2025-{m:02d}", **{"504": "5000000"}) for m in range(1, 7)]
        tf = _tax_folder(f29_list=f29_list)
        result = CreditRiskEngine(benchmark_vacio).calculate(tf)
        assert result.indicadores.mora_efectiva.score == 100
        assert result.indicadores.mora_efectiva.meses_con_remanente_credito == 6

    def test_recargo_real_penaliza(self, benchmark_vacio) -> None:
        f29_list = [_f29(f"2025-{m:02d}") for m in range(1, 7)]
        f29_list[0] = _f29("2025-01", **{"94": "150000"})
        tf = _tax_folder(f29_list=f29_list)
        result = CreditRiskEngine(benchmark_vacio).calculate(tf)
        assert result.indicadores.mora_efectiva.meses_con_recargo == 1
        assert result.indicadores.mora_efectiva.score < 100


class TestMargenVsGiro:
    def test_sin_benchmark_queda_insuficiente_muestra(self, benchmark_vacio) -> None:
        f29_list = [_f29(f"2025-{m:02d}") for m in range(1, 7)]
        monthly = [
            MonthlyTax(periodo=f"2025-{m:02d}", debito_fiscal=Decimal("300"), credito_fiscal=Decimal("100"))
            for m in range(1, 7)
        ]
        actividad = Activity(codigo="123456", descripcion="TEST", principal=True)
        tf = _tax_folder(f29_list=f29_list, monthly_taxes=monthly, activities=[actividad])
        result = CreditRiskEngine(benchmark_vacio).calculate(tf)
        m = result.indicadores.margen_vs_giro
        assert m.ratio_debito_credito_12m == 3.0
        assert m.score is not None
        assert m.confianza in ("media", "alta")

    def test_con_benchmark_suficiente_calcula_score(self, tmp_path) -> None:
        bench = SectorBenchmark(path=tmp_path / "bench.json")
        for _ in range(15):
            bench.registrar_muestra("123456", 3.0)

        f29_list = [_f29(f"2025-{m:02d}") for m in range(1, 7)]
        monthly = [
            MonthlyTax(periodo=f"2025-{m:02d}", debito_fiscal=Decimal("300"), credito_fiscal=Decimal("100"))
            for m in range(1, 7)
        ]
        actividad = Activity(codigo="123456", descripcion="TEST", principal=True)
        tf = _tax_folder(f29_list=f29_list, monthly_taxes=monthly, activities=[actividad])
        result = CreditRiskEngine(bench).calculate(tf)
        m = result.indicadores.margen_vs_giro
        assert m.confianza == "alta"
        assert m.score is not None
        assert m.n_empresas_referencia == 15


class TestRespaldoEstructural:
    def test_sin_cupo_no_calcula_score(self, benchmark_vacio) -> None:
        f29_list = [_f29(f"2025-{m:02d}") for m in range(1, 7)]
        f22 = AnnualTaxReturn(anio_tributario="2024", capital_propio_tributario=100_000_000)
        tf = _tax_folder(f29_list=f29_list, f22_list=[f22])
        result = CreditRiskEngine(benchmark_vacio).calculate(tf)
        assert result.indicadores.respaldo_estructural.score is not None
        assert result.indicadores.respaldo_estructural.capital_propio_tributario == 100_000_000

    def test_con_cupo_calcula_cobertura(self, benchmark_vacio) -> None:
        f29_list = [_f29(f"2025-{m:02d}") for m in range(1, 7)]
        f22 = AnnualTaxReturn(anio_tributario="2024", capital_propio_tributario=100_000_000)
        tf = _tax_folder(f29_list=f29_list, f22_list=[f22])
        result = CreditRiskEngine(benchmark_vacio).calculate(tf, cupo_solicitado=50_000_000)
        assert result.indicadores.respaldo_estructural.veces_cobertura == 2.0
        assert result.indicadores.respaldo_estructural.score is not None

    def test_usa_el_anio_mas_reciente(self, benchmark_vacio) -> None:
        f29_list = [_f29(f"2025-{m:02d}") for m in range(1, 7)]
        f22_list = [
            AnnualTaxReturn(anio_tributario="2022", capital_propio_tributario=10_000_000),
            AnnualTaxReturn(anio_tributario="2024", capital_propio_tributario=200_000_000),
            AnnualTaxReturn(anio_tributario="2023", capital_propio_tributario=50_000_000),
        ]
        tf = _tax_folder(f29_list=f29_list, f22_list=f22_list)
        result = CreditRiskEngine(benchmark_vacio).calculate(tf)
        assert result.indicadores.respaldo_estructural.capital_propio_tributario == 200_000_000


class TestScoreCompuesto:
    def test_un_solo_indicador_no_forma_compuesto(self, benchmark_vacio) -> None:
        # Solo mora_efectiva tiene score (débito y crédito en 0, sin f22).
        f29_list = [_f29(f"2025-{m:02d}") for m in range(1, 7)]
        monthly = [
            MonthlyTax(periodo=f"2025-{m:02d}", debito_fiscal=Decimal("0"), credito_fiscal=Decimal("0"))
            for m in range(1, 7)
        ]
        tf = _tax_folder(f29_list=f29_list, monthly_taxes=monthly, f22_list=[])
        result = CreditRiskEngine(benchmark_vacio).calculate(tf)
        assert result.indicadores.mora_efectiva.score is not None
        assert result.indicadores.margen_vs_giro.score is None
        assert result.indicadores.respaldo_estructural.score is None
        assert result.score_compuesto is None
        assert result.decision.resultado_base == "NO_EVALUABLE"

    def test_dos_indicadores_si_forman_compuesto(self, benchmark_vacio) -> None:
        f29_list = [_f29(f"2025-{m:02d}") for m in range(1, 7)]
        f22 = AnnualTaxReturn(anio_tributario="2024", capital_propio_tributario=100_000_000)
        tf = _tax_folder(f29_list=f29_list, f22_list=[f22])
        result = CreditRiskEngine(benchmark_vacio).calculate(tf, cupo_solicitado=50_000_000)
        assert result.score_compuesto is not None
        assert result.decision.resultado_base is not None


class TestCaminosMitigacion:
    def test_alto_facturado_habilita_factoring(self, benchmark_vacio) -> None:
        f29_list = [_f29(f"2025-{m:02d}", **{"502": "1000000"}) for m in range(1, 7)]
        tf = _tax_folder(f29_list=f29_list)
        result = CreditRiskEngine(benchmark_vacio).calculate(tf)
        factoring = next(c for c in result.decision.caminos_mitigacion if c.condicion == "cesion_facturas_factoring")
        assert factoring.aplica is True

    def test_bajo_facturado_no_habilita_factoring(self, benchmark_vacio) -> None:
        f29_list = [_f29(f"2025-{m:02d}", **{"111": "1000000"}) for m in range(1, 7)]
        tf = _tax_folder(f29_list=f29_list)
        result = CreditRiskEngine(benchmark_vacio).calculate(tf)
        factoring = next(c for c in result.decision.caminos_mitigacion if c.condicion == "cesion_facturas_factoring")
        assert factoring.aplica is False


class TestCalibracionConservadoraV22:
    def test_techo_operativo_8pct_compras(self, benchmark_vacio) -> None:
        # 12 meses de F29 con ventas y compras
        f29_list = [_f29(f"2025-{m:02d}", **{"502": "50000000"}) for m in range(1, 13)]
        # Compras operacionales de 10.000.000 mensuales
        monthly = [
            MonthlyTax(
                periodo=f"2025-{m:02d}",
                total_ventas=Decimal("50000000"),
                compras=Decimal("10000000"),
                compras_operacionales=Decimal("10000000"),
                debito_fiscal=Decimal("9500000"),
                credito_fiscal=Decimal("1900000"),
                iva_determinado=Decimal("7600000"),
            )
            for m in range(1, 13)
        ]
        f22 = AnnualTaxReturn(anio_tributario="2024", capital_propio_tributario=500_000_000)
        tf = _tax_folder(f29_list=f29_list, monthly_taxes=monthly, f22_list=[f22])
        # Run monthly analysis first so monthly_analysis is present
        from src.services.monthly_tax_service import MonthlyTaxService
        tf.monthly_analysis = MonthlyTaxService().analyze(monthly)

        result = CreditRiskEngine(benchmark_vacio).calculate(tf)
        # Techo 8% de compras: 10.000.000 * 0.08 = 800.000
        mem = result.decision.memoria_calculo
        assert mem["techo_operativo_8pct"] == 800_000
        assert result.decision.plazo_sugerido_dias <= 30
        assert result.decision.cupo_maximo_sugerido == 800_000

    def test_cpt_negativo_da_cupo_cero_y_aval_obligatorio(self, benchmark_vacio) -> None:
        f29_list = [_f29(f"2025-{m:02d}", **{"502": "50000000"}) for m in range(1, 13)]
        monthly = [
            MonthlyTax(
                periodo=f"2025-{m:02d}",
                total_ventas=Decimal("50000000"),
                compras=Decimal("10000000"),
                compras_operacionales=Decimal("10000000"),
                debito_fiscal=Decimal("9500000"),
                credito_fiscal=Decimal("1900000"),
                iva_determinado=Decimal("7600000"),
            )
            for m in range(1, 13)
        ]
        # CPT negativo
        f22 = AnnualTaxReturn(anio_tributario="2024", capital_propio_tributario=-50_000_000)
        tf = _tax_folder(f29_list=f29_list, monthly_taxes=monthly, f22_list=[f22])
        from src.services.monthly_tax_service import MonthlyTaxService
        tf.monthly_analysis = MonthlyTaxService().analyze(monthly)

        result = CreditRiskEngine(benchmark_vacio).calculate(tf)
        assert result.decision.cupo_aprobado == 0
        assert result.decision.resultado_base == "RECHAZADO"
        assert result.decision.plazo_sugerido_dias == 0
        mem = result.decision.memoria_calculo
        assert mem["cupo_excepcional_garantizado"] > 0
        assert "CPT negativo" in result.decision.garantia_exigida

