from decimal import Decimal

from pydantic import BaseModel

from src.models.monthly_tax import MonthlyTax


class MonthlyTaxResult(BaseModel):
    monthly_taxes: list[MonthlyTax]
    total_months: int
    ventas_ultimos_12: Decimal | None = None
    compras_ultimos_12: Decimal | None = None
    promedio_ventas_mensual: Decimal | None = None
    promedio_compras_mensual: Decimal | None = None
    crecimiento_anual: Decimal | None = None
    meses_sin_movimiento: int = 0
    mejor_mes: str | None = None
    peor_mes: str | None = None


class MonthlyTaxService:
    def analyze(self, monthly_taxes: list[MonthlyTax]) -> MonthlyTaxResult:
        if not monthly_taxes:
            return MonthlyTaxResult(monthly_taxes=[], total_months=0)

        total = len(monthly_taxes)
        last_12 = monthly_taxes[-12:] if total >= 12 else monthly_taxes

        ventas_u12 = self._sum_field(last_12, "total_ventas")
        compras_u12 = self._sum_field(last_12, "compras")
        prom_ventas = ventas_u12 / Decimal(str(len(last_12))) if ventas_u12 is not None else None
        prom_compras = compras_u12 / Decimal(str(len(last_12))) if compras_u12 is not None else None

        crecimiento = self._calc_crecimiento(monthly_taxes)

        meses_sin = sum(
            1 for m in monthly_taxes
            if (m.total_ventas is None or m.total_ventas == 0)
        )

        mejor, peor = self._best_worst_month(monthly_taxes)

        return MonthlyTaxResult(
            monthly_taxes=monthly_taxes,
            total_months=total,
            ventas_ultimos_12=ventas_u12,
            compras_ultimos_12=compras_u12,
            promedio_ventas_mensual=prom_ventas,
            promedio_compras_mensual=prom_compras,
            crecimiento_anual=crecimiento,
            meses_sin_movimiento=meses_sin,
            mejor_mes=mejor,
            peor_mes=peor,
        )

    @staticmethod
    def _sum_field(monthly: list[MonthlyTax], field: str) -> Decimal | None:
        vals = [getattr(m, field) for m in monthly if getattr(m, field) is not None]
        if not vals:
            return None
        return sum(vals, Decimal("0"))

    @staticmethod
    def _calc_crecimiento(monthly: list[MonthlyTax]) -> Decimal | None:
        if len(monthly) < 12:
            return None
        # compare first 6 months vs last 6 months of total_ventas
        mid = len(monthly) // 2
        first_half = [m.total_ventas for m in monthly[:mid] if m.total_ventas is not None]
        second_half = [m.total_ventas for m in monthly[-mid:] if m.total_ventas is not None]
        if not first_half or not second_half:
            return None
        s1 = sum(first_half, Decimal("0"))
        s2 = sum(second_half, Decimal("0"))
        if s1 == 0:
            return None
        return ((s2 - s1) / s1 * 100).quantize(Decimal("0.01"))

    @staticmethod
    def _best_worst_month(monthly: list[MonthlyTax]) -> tuple[str | None, str | None]:
        best = worst = None
        best_val: Decimal | None = None
        worst_val: Decimal | None = None
        for m in monthly:
            tv = m.total_ventas
            if tv is None:
                continue
            if best_val is None or tv > best_val:
                best_val = tv
                best = m.periodo
            if worst_val is None or tv < worst_val:
                worst_val = tv
                worst = m.periodo
        return best, worst
