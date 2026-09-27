from decimal import Decimal

from src.models.monthly_tax import (
    MonthlyTax,
    MonthlyTaxAnalysis,
    MonthlyTaxResult,
)


class MonthlyTaxService:
    def analyze(self, monthly_taxes: list[MonthlyTax]) -> MonthlyTaxResult:
        if not monthly_taxes:
            return MonthlyTaxResult(monthly_taxes=[], total_months=0)

        total = len(monthly_taxes)
        sorted_taxes = sorted(monthly_taxes, key=lambda m: m.periodo or "")
        last_12 = sorted_taxes[-12:] if total >= 12 else sorted_taxes
        last_3 = sorted_taxes[-3:] if total >= 3 else sorted_taxes

        ventas_u12 = self._sum_field(last_12, "total_ventas")
        compras_u12 = self._sum_field(last_12, "compras")
        prom_ventas = ventas_u12 / Decimal(str(len(last_12))) if ventas_u12 is not None else None
        prom_compras = compras_u12 / Decimal(str(len(last_12))) if compras_u12 is not None else None

        ventas_u3 = self._sum_field(last_3, "total_ventas")
        compras_u3 = self._sum_field(last_3, "compras")
        prom_ventas_3m = ventas_u3 / Decimal(str(len(last_3))) if ventas_u3 is not None else None
        prom_compras_3m = compras_u3 / Decimal(str(len(last_3))) if compras_u3 is not None else None

        compras_op_sum = sum(
            (m.compras_operacionales if m.compras_operacionales is not None else (m.compras or Decimal("0")))
            for m in last_12
        )
        prom_compras_op_12m = (
            compras_op_sum / Decimal(str(len(last_12))) if last_12 else None
        )

        compras_op_sum_3m = sum(
            (m.compras_operacionales if m.compras_operacionales is not None else (m.compras or Decimal("0")))
            for m in last_3
        )
        prom_compras_op_3m = (
            compras_op_sum_3m / Decimal(str(len(last_3))) if last_3 else None
        )

        # Variación porcentual ventas 3M vs 12M
        if prom_ventas and prom_ventas > 0 and prom_ventas_3m is not None:
            var_ventas_3m = (
                (prom_ventas_3m - prom_ventas) / prom_ventas * 100
            ).quantize(Decimal("0.01"))
        else:
            var_ventas_3m = None

        # Margen implícito depurado (Débito / Crédito operacional sin remanente 504)
        deb_12 = self._sum_field(last_12, "debito_fiscal")
        cred_op_12 = self._sum_field(last_12, "credito_operacional")
        if cred_op_12 is None or cred_op_12 == 0:
            cred_op_12 = self._sum_field(last_12, "credito_fiscal")
        margen_12 = (
            (deb_12 / cred_op_12).quantize(Decimal("0.001"))
            if deb_12 is not None and cred_op_12 and cred_op_12 > 0
            else None
        )

        deb_3 = self._sum_field(last_3, "debito_fiscal")
        cred_op_3 = self._sum_field(last_3, "credito_operacional")
        if cred_op_3 is None or cred_op_3 == 0:
            cred_op_3 = self._sum_field(last_3, "credito_fiscal")
        margen_3 = (
            (deb_3 / cred_op_3).quantize(Decimal("0.001"))
            if deb_3 is not None and cred_op_3 and cred_op_3 > 0
            else None
        )

        # Costo Operativo Proxy para empresas de servicios, salud o rentistas (compras < 15% ventas)
        # Costo = compras_operacionales + (retencion_honorarios / 0.1375) + (impuesto_unico * 15)
        # Piso = 30% de ventas mensuales promedio
        costos_proxy_12m = []
        for m in last_12:
            cop = m.compras_operacionales if m.compras_operacionales is not None else (m.compras or Decimal("0"))
            hon = (m.retencion_honorarios / Decimal("0.1375")) if (m.retencion_honorarios and m.retencion_honorarios > 0) else Decimal("0")
            sue = (m.retencion_sueldos * Decimal("15")) if (m.retencion_sueldos and m.retencion_sueldos > 0) else Decimal("0")
            costos_proxy_12m.append(cop + hon + sue)

        prom_costo_proxy = (sum(costos_proxy_12m, Decimal("0")) / Decimal(str(len(last_12)))) if last_12 else Decimal("0")
        piso_30 = (prom_ventas * Decimal("0.30")) if prom_ventas else Decimal("0")
        promedio_costo_operativo_proxy_12m = max(prom_costo_proxy, piso_30) if prom_ventas else prom_costo_proxy

        costo_proxy_aplica = False
        if ventas_u12 and ventas_u12 > 0:
            cop_total = compras_op_sum or compras_u12 or Decimal("0")
            if cop_total < (ventas_u12 * Decimal("0.15")):
                costo_proxy_aplica = True
        elif not compras_op_sum or compras_op_sum == 0:
            costo_proxy_aplica = True

        # Variación YoY trimestral (mismos 3 meses del año anterior)
        var_ventas_yoy_3m = None
        if total >= 15 and prom_ventas_3m is not None:
            pmap = {m.periodo: m.total_ventas for m in monthly_taxes if m.periodo and m.total_ventas is not None}
            ventas_yoy_m = []
            for m in last_3:
                if m.periodo and len(m.periodo) == 7 and m.periodo[:4].isdigit():
                    prev_p = f"{int(m.periodo[:4]) - 1}{m.periodo[4:]}"
                    if prev_p in pmap:
                        ventas_yoy_m.append(pmap[prev_p])
            if ventas_yoy_m:
                prom_yoy_3m = sum(ventas_yoy_m, Decimal("0")) / Decimal(str(len(ventas_yoy_m)))
                if prom_yoy_3m > 0:
                    var_ventas_yoy_3m = (
                        (prom_ventas_3m - prom_yoy_3m) / prom_yoy_3m * 100
                    ).quantize(Decimal("0.01"))

        ret_12 = self._sum_field(last_12, "retenciones_totales")
        ret_3 = self._sum_field(last_3, "retenciones_totales")

        crecimiento = self._calc_crecimiento(monthly_taxes)

        meses_sin = sum(
            1 for m in monthly_taxes
            if (m.total_ventas is None or m.total_ventas == 0)
        )

        # Tendencia ventas trimestral (3M vs 12M promedio)
        tasa_crec_ventas_3m = None
        if prom_ventas and prom_ventas > 0 and prom_ventas_3m is not None:
            tasa_crec_ventas_3m = float((prom_ventas_3m - prom_ventas) / prom_ventas)
        elif var_ventas_3m is not None:
            tasa_crec_ventas_3m = float(var_ventas_3m) / 100.0

        # Tendencia compras trimestral (3M vs 12M promedio)
        tasa_crec_compras_3m = None
        if prom_compras and prom_compras > 0 and prom_compras_3m is not None:
            tasa_crec_compras_3m = float((prom_compras_3m - prom_compras) / prom_compras)

        # Margen operacional implícito promedio (12M): (Ventas - Compras Op) / Ventas
        margen_op_prom = None
        if ventas_u12 and ventas_u12 > 0:
            c_op = compras_op_sum if compras_op_sum is not None else compras_u12
            if c_op is not None:
                margen_op_prom = float((ventas_u12 - c_op) / ventas_u12)
        elif margen_12 is not None:
            margen_op_prom = float(margen_12)

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
            promedio_ventas_ultimos_3m=prom_ventas_3m,
            promedio_compras_ultimos_3m=prom_compras_3m,
            promedio_compras_operacionales_12m=prom_compras_op_12m,
            promedio_compras_operacionales_3m=prom_compras_op_3m,
            variacion_ventas_3m_pct=var_ventas_3m,
            variacion_ventas_yoy_3m_pct=var_ventas_yoy_3m,
            promedio_costo_operativo_proxy_12m=promedio_costo_operativo_proxy_12m,
            costo_operativo_proxy_aplica=costo_proxy_aplica,
            margen_implicito_12m=margen_12,
            margen_implicito_3m=margen_3,
            retenciones_totales_12m=ret_12,
            retenciones_totales_3m=ret_3,
            tasa_crecimiento_ventas_trimestral=tasa_crec_ventas_3m,
            tasa_crecimiento_compras_trimestral=tasa_crec_compras_3m,
            margen_operacional_implicito_promedio=margen_op_prom,
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
