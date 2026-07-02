from pydantic import BaseModel


class Activity(BaseModel):
    codigo: str
    descripcion: str
    principal: bool = False
    categoria: str | None = None
    fecha_inicio: str | None = None
