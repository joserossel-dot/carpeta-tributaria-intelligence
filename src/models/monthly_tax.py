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
    compras_operacionales: Decimal | None = None
    credito_operacional: Decimal | None = None
    activo_fijo: Decimal | None = None
    remanente_anterior: Decimal | None = None
    notas_credito_compras: Decimal | None = None
    retencion_sueldos: Decimal | None = None
    retencion_honorarios: Decimal | None = None
    retenciones_totales: Decimal | None = None
    observaciones: list[str] = []

