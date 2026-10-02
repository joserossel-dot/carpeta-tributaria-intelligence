from __future__ import annotations

from decimal import Decimal
from pydantic import BaseModel, ConfigDict


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


class MonthlyTaxResult(BaseModel):
    """Resultado del análisis mensual de IVA y dinamismo comercial."""
    model_config = ConfigDict(extra="allow")

    monthly_taxes: list[MonthlyTax] = []
    total_months: int = 0
    ventas_ultimos_12: Decimal | None = None
    compras_ultimos_12: Decimal | None = None
    promedio_ventas_mensual: Decimal | None = None
    promedio_compras_mensual: Decimal | None = None
    crecimiento_anual: Decimal | None = None
    meses_sin_movimiento: int = 0
    mejor_mes: str | None = None
    peor_mes: str | None = None
    promedio_ventas_ultimos_3m: Decimal | None = None
    promedio_compras_ultimos_3m: Decimal | None = None
    promedio_compras_operacionales_12m: Decimal | None = None
    promedio_compras_operacionales_3m: Decimal | None = None
    variacion_ventas_3m_pct: Decimal | None = None
    margen_implicito_12m: Decimal | None = None
    margen_implicito_3m: Decimal | None = None
    retenciones_totales_12m: Decimal | None = None
    retenciones_totales_3m: Decimal | None = None
    variacion_ventas_yoy_3m_pct: Decimal | None = None
    promedio_costo_operativo_proxy_12m: Decimal | None = None
    costo_operativo_proxy_aplica: bool = False

    # Campos y aliases para componentes visuales y reporte ejecutivo
    tasa_crecimiento_ventas_trimestral: float | None = None
    tasa_crecimiento_compras_trimestral: float | None = None
    margen_operacional_implicito_promedio: float | None = None


# Alias compatible hacia atrás
MonthlyTaxAnalysis = MonthlyTaxResult
