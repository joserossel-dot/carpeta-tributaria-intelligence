from pydantic import BaseModel


class Contributor(BaseModel):
    rut: str | None = None
    razon_social: str | None = None
    fecha_generacion: str | None = None
    fecha_inicio_actividades: str | None = None
    domicilio: str | None = None
    comuna: str | None = None
    region: str | None = None
    tipo_contribuyente: str | None = None
    regimen_tributario: str | None = None
