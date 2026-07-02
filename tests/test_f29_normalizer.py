from src.models.f29 import F29, F29Detail
from src.normalizers.f29_normalizer import normalize_f29


class TestNormalizeF29:
    def test_normalize_period(self) -> None:
        forms = [F29(periodo="12/2019", folio="123", fecha_presentacion="28/01/2020", detalles=[])]
        result = normalize_f29(forms)
        assert result[0].periodo == "2019-12"

    def test_normalize_fecha_presentacion(self) -> None:
        forms = [F29(periodo="2020-01", folio="123", fecha_presentacion="28/01/2020", detalles=[])]
        result = normalize_f29(forms)
        assert result[0].fecha_presentacion == "2020-01-28"

    def test_fecha_presentacion_no_normalizable(self) -> None:
        forms = [F29(periodo="2020-01", folio="123", fecha_presentacion="invalida", detalles=[])]
        result = normalize_f29(forms)
        assert result[0].fecha_presentacion == "invalida"

    def test_fecha_presentacion_none(self) -> None:
        forms = [F29(periodo="2020-01", folio="123", fecha_presentacion=None, detalles=[])]
        result = normalize_f29(forms)
        assert result[0].fecha_presentacion is None

    def test_normalize_money(self) -> None:
        forms = [
            F29(
                periodo="2020-01",
                folio="123",
                fecha_presentacion=None,
                detalles=[
                    F29Detail(codigo="503", glosa="  FACTURAS  ", valor="  236.141.139  "),
                    F29Detail(codigo="502", glosa="DEBITOS", valor="1,60"),
                ],
            )
        ]
        result = normalize_f29(forms)
        assert result[0].detalles[0].valor == "236141139"
        assert result[0].detalles[1].valor == "1.60"

    def test_normalize_glosa(self) -> None:
        forms = [
            F29(
                periodo="2020-01",
                folio="123",
                fecha_presentacion=None,
                detalles=[F29Detail(codigo="503", glosa="  CANTIDAD  FACTURAS  ", valor="26")],
            )
        ]
        result = normalize_f29(forms)
        assert result[0].detalles[0].glosa == "CANTIDAD FACTURAS"

    def test_empty_list(self) -> None:
        result = normalize_f29([])
        assert result == []

    def test_multiple_forms(self) -> None:
        forms = [
            F29(periodo="2019-12", folio="001", fecha_presentacion=None, detalles=[]),
            F29(periodo="2020-01", folio="002", fecha_presentacion="15/02/2020", detalles=[]),
        ]
        result = normalize_f29(forms)
        assert len(result) == 2
        assert result[1].fecha_presentacion == "2020-02-15"

    def test_preserves_folio(self) -> None:
        forms = [F29(periodo="2020-01", folio="  6904798236  ", fecha_presentacion=None, detalles=[])]
        result = normalize_f29(forms)
        assert result[0].folio == "6904798236"
