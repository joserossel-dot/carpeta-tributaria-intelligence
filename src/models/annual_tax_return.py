from pydantic import BaseModel


class AnnualTaxReturn(BaseModel):
    anio_tributario: str | None = None
    ingresos: int | None = None
    renta_liquida_imponible: int | None = None
    capital_propio_tributario: int | None = None
    impuesto_determinado: int | None = None
    ppm: int | None = None
    creditos: int | None = None
    perdidas: int | None = None
    base_imponible: int | None = None
    resultado_tributario: int | None = None
    observaciones: list[str] = []
