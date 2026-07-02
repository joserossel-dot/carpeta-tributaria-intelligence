from decimal import Decimal
from datetime import datetime


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
