from decimal import Decimal

from src.models.monthly_tax import MonthlyTax
from src.services.monthly_tax_service import MonthlyTaxService


class TestMonthlyTaxService:
    def _mt(self, periodo: str, ventas: int | None, compras: int | None = None) -> MonthlyTax:
        return MonthlyTax(
            periodo=periodo,
            total_ventas=Decimal(str(ventas)) if ventas is not None else None,
            compras=Decimal(str(compras)) if compras is not None else None,
        )

    def test_empty(self) -> None:
        svc = MonthlyTaxService()
        res = svc.analyze([])
        assert res.total_months == 0
        assert res.monthly_taxes == []

    def test_single_month(self) -> None:
        svc = MonthlyTaxService()
        res = svc.analyze([self._mt("2024-01", 1000)])
        assert res.total_months == 1
        assert res.ventas_ultimos_12 == Decimal("1000")
        assert res.promedio_ventas_mensual == Decimal("1000")
        assert res.crecimiento_anual is None
        assert res.meses_sin_movimiento == 0
        assert res.mejor_mes == "2024-01"
        assert res.peor_mes == "2024-01"

    def test_two_months(self) -> None:
        svc = MonthlyTaxService()
        res = svc.analyze([
            self._mt("2024-01", 1000),
            self._mt("2024-02", 2000),
        ])
        assert res.total_months == 2
        assert res.ventas_ultimos_12 == Decimal("3000")  # both within 12 months
        assert res.promedio_ventas_mensual == Decimal("1500")
        assert res.mejor_mes == "2024-02"
        assert res.peor_mes == "2024-01"

    def test_12_months(self) -> None:
        svc = MonthlyTaxService()
        taxes = [self._mt(f"2024-{m:02d}", 1000 * m) for m in range(1, 13)]
        res = svc.analyze(taxes)
        assert res.total_months == 12
        assert res.ventas_ultimos_12 == sum(Decimal(str(1000 * m)) for m in range(1, 13))
        assert res.crecimiento_anual is not None

    def test_meses_sin_movimiento(self) -> None:
        svc = MonthlyTaxService()
        taxes = [
            self._mt("2024-01", 1000),
            self._mt("2024-02", 0),
            self._mt("2024-03", None),
            self._mt("2024-04", 500),
        ]
        res = svc.analyze(taxes)
        assert res.meses_sin_movimiento == 2

    def test_best_worst_month(self) -> None:
        svc = MonthlyTaxService()
        taxes = [
            self._mt("2024-01", 100),
            self._mt("2024-02", 500),
            self._mt("2024-03", 50),
        ]
        res = svc.analyze(taxes)
        assert res.mejor_mes == "2024-02"
        assert res.peor_mes == "2024-03"

    def test_last_12_filtering(self) -> None:
        svc = MonthlyTaxService()
        # 14 months — last_12 should only include the last 12
        taxes = [self._mt(f"2023-{m:02d}", 100) for m in range(1, 13)]
        taxes.extend([self._mt("2024-01", 200), self._mt("2024-02", 300)])
        res = svc.analyze(taxes)
        assert res.total_months == 14
        # last 12 should include 2023-03 through 2024-02
        assert res.ventas_ultimos_12 == Decimal("100") * 10 + Decimal("200") + Decimal("300")
        assert res.promedio_ventas_mensual == (Decimal("100") * 10 + Decimal("200") + Decimal("300")) / Decimal("12")
