from pydantic import BaseModel


class F29Detail(BaseModel):
    codigo: str
    glosa: str
    valor: str


class F29(BaseModel):
    periodo: str
    folio: str
    fecha_presentacion: str | None = None
    detalles: list[F29Detail]
