from src.models.contributor import Contributor
from src.normalizers.contributor_normalizer import normalize_contributor


class TestNormalizeContributor:
    def test_normalize_rut(self) -> None:
        c = normalize_contributor(Contributor(rut="79.606.270-3"))
        assert c.rut == "79606270-3"

    def test_normalize_razon_social(self) -> None:
        c = normalize_contributor(Contributor(razon_social="  agricola  ltda  "))
        assert c.razon_social == "AGRICOLA LTDA"

    def test_normalize_fecha_generacion(self) -> None:
        c = normalize_contributor(Contributor(fecha_generacion="30/01/2020 10:40"))
        assert c.fecha_generacion == "2020-01-30"

    def test_normalize_fecha_inicio_valida(self) -> None:
        c = normalize_contributor(Contributor(fecha_inicio_actividades="05-06-2000"))
        assert c.fecha_inicio_actividades == "2000-06-05"

    def test_fecha_inicio_no_normalizable(self) -> None:
        c = normalize_contributor(Contributor(fecha_inicio_actividades="  Anterior a 1993  "))
        assert c.fecha_inicio_actividades == "  Anterior a 1993  "

    def test_normalize_domicilio(self) -> None:
        c = normalize_contributor(Contributor(domicilio="  Fundo  Santa  María  "))
        assert c.domicilio == "Fundo Santa María"

    def test_normalize_comuna(self) -> None:
        c = normalize_contributor(Contributor(comuna="  molina  "))
        assert c.comuna == "MOLINA"

    def test_normalize_tipo_contribuyente(self) -> None:
        c = normalize_contributor(Contributor(tipo_contribuyente="  Primera categoría  "))
        assert c.tipo_contribuyente == "Primera categoría"

    def test_normalize_regimen(self) -> None:
        c = normalize_contributor(Contributor(regimen_tributario="  REGIMEN PRO PYME  "))
        assert c.regimen_tributario == "REGIMEN PRO PYME"

    def test_all_fields_none(self) -> None:
        c = normalize_contributor(Contributor())
        assert c.rut is None
        assert c.razon_social is None
        assert c.fecha_generacion is None

    def test_preserves_region(self) -> None:
        c = normalize_contributor(Contributor(region="Metropolitana"))
        assert c.region == "Metropolitana"
