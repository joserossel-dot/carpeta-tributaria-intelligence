from src.models.f29 import F29, F29Detail
from src.normalizers.common import normalize_date, normalize_money, normalize_period, normalize_text


def normalize_f29(forms: list[F29]) -> list[F29]:
    result: list[F29] = []
    for form in forms:
        periodo = normalize_period(form.periodo) or form.periodo
        raw = form.fecha_presentacion.strip() if form.fecha_presentacion else None
        fecha = normalize_date(raw) if raw else None
        if raw and not fecha:
            fecha = raw
        detalles = [
            F29Detail(
                codigo=d.codigo.strip(),
                glosa=normalize_text(d.glosa),
                valor=normalize_money(d.valor),
            )
            for d in form.detalles
        ]
        result.append(F29(periodo=periodo, folio=form.folio.strip(), fecha_presentacion=fecha, detalles=detalles))
    return result
