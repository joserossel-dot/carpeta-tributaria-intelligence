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
    idpc_determinado: int | None = None
    ppm_imputados: int | None = None
    saldo_liquidacion_anual: int | None = None
    rli_source_code: str | None = None
    cpt_source_code: str | None = None
    ingresos_source_code: str | None = None

    @property
    def resultado_financiero(self) -> int | None:
        return self.resultado_tributario
