from src.models.contributor import Contributor
from src.normalizers.common import normalize_date, normalize_rut, normalize_text


def normalize_contributor(contributor: Contributor) -> Contributor:
    data = contributor.model_dump()

    if data.get("rut"):
        data["rut"] = normalize_rut(data["rut"])

    if data.get("razon_social"):
        data["razon_social"] = normalize_text(data["razon_social"]).upper()

    for field in ("fecha_generacion", "fecha_inicio_actividades"):
        if data.get(field):
            val = str(data[field]).strip()
            first = val.split()[0]
            normalized = normalize_date(first)
            if normalized:
                data[field] = normalized

    if data.get("domicilio"):
        data["domicilio"] = normalize_text(data["domicilio"])

    if data.get("comuna"):
        data["comuna"] = normalize_text(data["comuna"]).upper()

    if data.get("tipo_contribuyente"):
        data["tipo_contribuyente"] = normalize_text(data["tipo_contribuyente"])

    if data.get("regimen_tributario"):
        data["regimen_tributario"] = normalize_text(data["regimen_tributario"])

    return Contributor(**data)
