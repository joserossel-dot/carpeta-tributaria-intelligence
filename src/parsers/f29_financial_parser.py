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
                monthly[periodo]["compras"] = None
                observaciones[periodo] = []

            row = monthly[periodo]
            obs = observaciones[periodo]

            for det in f29.detalles:
                campo = self.CODE_MAP.get(det.codigo)
                if not campo and det.codigo != self.COMPRAS_CREDIT_CODE:
                    continue
                valor = self._parse_valor(det.valor)
                if valor is None:
                    continue
                if det.codigo == self.COMPRAS_CREDIT_CODE:
                    # derive purchase amount from VAT credit ÷ 0.19
                    compras = self._credit_to_purchases(valor)
                    if compras is not None:
                        if row["compras"] is None:
                            row["compras"] = compras
                        else:
                            row["compras"] += compras
                elif campo:
                    if row[campo] is None:
                        row[campo] = valor
                    else:
                        row[campo] += valor

        result: list[MonthlyTax] = []
        for periodo in sorted(monthly.keys()):
            row = monthly[periodo]
            obs = observaciones[periodo]
            ventas_afectas = row["ventas_afectas"]
            ventas_exentas = row["ventas_exentas"]
            ventas_exportacion = row["ventas_exportacion"]
            total_ventas = self._sumar(ventas_afectas, ventas_exentas, ventas_exportacion)
            result.append(MonthlyTax(
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
                observaciones=obs,
            ))

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
