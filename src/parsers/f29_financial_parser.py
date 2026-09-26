from decimal import Decimal

from src.models.f29 import F29
from src.models.monthly_tax import MonthlyTax


class F29FinancialParser:
    CODE_MAP: dict[str, str] = {
        "563": "ventas_afectas",
        "142": "ventas_exentas",
        "020": "ventas_exportacion",
        "538": "debito_fiscal",
        "537": "credito_fiscal",
        "089": "iva_determinado",
        "062": "ppm",
    }

    # Códigos operacionales adicionales
    EXTRA_CODES: dict[str, str] = {
        "511": "credito_511",
        "520": "credito_520",
        "525": "credito_activo_fijo_525",
        "528": "credito_nc_528",
        "527": "cant_nc_527",
        "514": "credito_importaciones_514",
        "536": "credito_importaciones_536",
        "562": "compras_no_credito_562",
        "584": "compras_exentas_584",
        "504": "remanente_504",
        "048": "retencion_sueldos_048",
        "151": "retencion_honorarios_151",
    }

    # código 511 = CRÉD. IVA POR DCTOS. ELECTRONICOS = 19% of purchases
    COMPRAS_CREDIT_CODE = "511"
    IVA_RATE = Decimal("0.19")

    def parse(self, f29_list: list[F29]) -> list[MonthlyTax]:
        monthly: dict[str, dict[str, Decimal | None]] = {}
        observaciones: dict[str, list[str]] = {}

        for f29 in f29_list:
            periodo = f29.periodo
            if periodo not in monthly:
                monthly[periodo] = {v: None for v in self.CODE_MAP.values()}
                for v in self.EXTRA_CODES.values():
                    monthly[periodo][v] = None
                monthly[periodo]["compras"] = None
                observaciones[periodo] = []

            row = monthly[periodo]
            obs = observaciones[periodo]

            for det in f29.detalles:
                campo = self.CODE_MAP.get(det.codigo)
                extra_campo = self.EXTRA_CODES.get(det.codigo)
                valor = self._parse_valor(det.valor)
                if valor is None:
                    continue

                if det.codigo == self.COMPRAS_CREDIT_CODE:
                    # derive purchase amount from VAT credit ÷ 0.19 (legacy compatibility)
                    compras = self._credit_to_purchases(valor)
                    if compras is not None:
                        if row["compras"] is None:
                            row["compras"] = compras
                        else:
                            row["compras"] += compras

                if campo:
                    if row[campo] is None:
                        row[campo] = valor
                    else:
                        row[campo] += valor

                if extra_campo:
                    if row[extra_campo] is None:
                        row[extra_campo] = valor
                    else:
                        row[extra_campo] += valor

        result: list[MonthlyTax] = []
        for periodo in sorted(monthly.keys()):
            row = monthly[periodo]
            obs = observaciones[periodo]
            ventas_afectas = row["ventas_afectas"]
            ventas_exentas = row["ventas_exentas"]
            ventas_exportacion = row["ventas_exportacion"]
            total_ventas = self._sumar(ventas_afectas, ventas_exentas, ventas_exportacion)

            # Crédito operacional del mes = max(0, Cód. 537 - Cód. 504 - Cód. 525)
            credito_total = row["credito_fiscal"]
            remanente_504 = row["remanente_504"]
            activo_fijo_cred = row["credito_activo_fijo_525"]
            nc_cred = row["credito_nc_528"]

            if credito_total is not None:
                credito_operacional = max(
                    Decimal("0"),
                    credito_total
                    - (remanente_504 or Decimal("0"))
                    - (activo_fijo_cred or Decimal("0")),
                )
            elif row["credito_520"] is not None or row["credito_511"] is not None:
                c_base = row["credito_520"] or row["credito_511"] or Decimal("0")
                credito_operacional = max(Decimal("0"), c_base - (nc_cred or Decimal("0")))
            else:
                credito_operacional = None

            # Compras operacionales del giro
            if credito_operacional is not None:
                compras_afectas = (
                    (credito_operacional / self.IVA_RATE).quantize(Decimal("0"))
                    if credito_operacional > 0
                    else Decimal("0")
                )
                compras_exentas = (row["compras_no_credito_562"] or Decimal("0")) + (
                    row["compras_exentas_584"] or Decimal("0")
                )
                compras_operacionales = compras_afectas + compras_exentas
            elif row["compras"] is not None:
                compras_operacionales = row["compras"]
            else:
                compras_operacionales = None

            # Activo fijo (monto neto estimado si hay crédito Cód. 525)
            activo_fijo_monto = (
                (activo_fijo_cred / self.IVA_RATE).quantize(Decimal("0"))
                if activo_fijo_cred
                else None
            )

            ret_sueldos = row["retencion_sueldos_048"]
            ret_honorarios = row["retencion_honorarios_151"]
            ret_totales = self._sumar(ret_sueldos, ret_honorarios)

            result.append(
                MonthlyTax(
                    periodo=periodo,
                    ventas_afectas=ventas_afectas,
                    ventas_exentas=ventas_exentas,
                    ventas_exportacion=ventas_exportacion,
                    compras=row["compras"],
                    debito_fiscal=row["debito_fiscal"],
                    credito_fiscal=row["credito_fiscal"],
                    iva_determinado=row["iva_determinado"],
                    ppm=row["ppm"],
                    total_ventas=total_ventas,
                    compras_operacionales=compras_operacionales,
                    credito_operacional=credito_operacional,
                    activo_fijo=activo_fijo_monto,
                    remanente_anterior=remanente_504,
                    notas_credito_compras=nc_cred,
                    retencion_sueldos=ret_sueldos,
                    retencion_honorarios=ret_honorarios,
                    retenciones_totales=ret_totales,
                    observaciones=obs,
                )
            )

        return result

    @staticmethod
    def _parse_valor(valor: str) -> Decimal | None:
        if not valor:
            return None
        try:
            return Decimal(valor.replace(".", "").replace(",", "."))
        except Exception:
            return None

    @staticmethod
    def _credit_to_purchases(credit: Decimal) -> Decimal | None:
        if credit == 0:
            return Decimal("0")
        return (credit / F29FinancialParser.IVA_RATE).quantize(Decimal("0"))

    @staticmethod
    def _sumar(*args: Decimal | None) -> Decimal | None:
        vals = [v for v in args if v is not None]
        if not vals:
            return None
        return sum(vals, Decimal("0"))

