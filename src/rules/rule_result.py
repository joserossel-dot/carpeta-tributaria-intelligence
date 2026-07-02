from pydantic import BaseModel


class RuleResult(BaseModel):
    nombre: str
    severidad: str
    mensaje: str
    categoria: str
    recomendado: str
