from decimal import Decimal

from pydantic import BaseModel


class MonthlyTax(BaseModel):
    periodo: str
    ventas_afectas: Decimal | None = None
    ventas_exentas: Decimal | None = None
    ventas_exportacion: Decimal | None = None
    compras: Decimal | None = None
    debito_fiscal: Decimal | None = None
    credito_fiscal: Decimal | None = None
    iva_determinado: Decimal | None = None
    ppm: Decimal | None = None
    total_ventas: Decimal | None = None
    observaciones: list[str] = []
