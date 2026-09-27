from datetime import datetime
from decimal import Decimal


def fmt_miles(val: int | float | Decimal | None) -> str:
    if val is None:
        return "—"
    if isinstance(val, Decimal):
        val = float(val)
    return f"{val:,.0f}".replace(",", ".")


def fmt_currency(val: int | float | Decimal | None) -> str:
    if val is None:
        return "—"
    return f"${fmt_miles(val)}"


def format_mclp(valor_clp: float | int | Decimal | None) -> str:
    """Divide los montos en pesos por 1.000 y formatea con separador de miles con puntos y prefijo 'M$'.
    Ejemplo: $12.345.678 -> 'M$ 12.346', $0 -> 'M$ 0', None -> '—'.
    """
    if valor_clp is None:
        return "—"
    if isinstance(valor_clp, Decimal):
        valor_clp = float(valor_clp)
    miles = round(valor_clp / 1000.0)
    if miles < 0:
        return f"-M$ {abs(miles):,.0f}".replace(",", ".")
    return f"M$ {miles:,.0f}".replace(",", ".")


def fmt_date(val: str | None) -> str:
    if not val:
        return "—"
    for fmt_in in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(val, fmt_in)
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            continue
    return val
