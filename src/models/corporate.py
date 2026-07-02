from pydantic import BaseModel


class Socio(BaseModel):
    rut: str
    nombre: str
    participacion: str | None = None


class Representante(BaseModel):
    rut: str
    nombre: str
    cargo: str | None = None


class CorporateInfo(BaseModel):
    tipo_sociedad: str | None = None
    fecha_constitucion: str | None = None
    capital: str | None = None
    socios: list[Socio] = []
    representantes: list[Representante] = []
