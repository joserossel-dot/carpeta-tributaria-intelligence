from src.models.activity import Activity
from src.models.company import Company
from src.models.contributor import Contributor
from src.models.f29 import F29
from src.rules.rule_engine import RuleEngine
from src.rules.tax_rules import (
    MultiplesActividadesPrincipalesRule,
    SinActividadesRule,
    SinF29Rule,
    SinRegimenTributarioRule,
    SinRepresentantesRule,
)


class TestSinActividadesRule:
    def test_triggers_when_no_activities(self) -> None:
        company = Company()
        result = SinActividadesRule().evaluate(company)
        assert result is not None
        assert "actividades" in result.mensaje.lower()

    def test_not_triggered_with_activities(self) -> None:
        company = Company(activities=[Activity(codigo="012400", descripcion="CULTIVO")])
        assert SinActividadesRule().evaluate(company) is None


class TestSinF29Rule:
    def test_triggers_when_no_f29(self) -> None:
        company = Company()
        result = SinF29Rule().evaluate(company)
        assert result is not None
        assert "F29" in result.mensaje

    def test_not_triggered_with_f29(self) -> None:
        company = Company(f29=[F29(periodo="2024-01", folio="1", detalles=[])])
        assert SinF29Rule().evaluate(company) is None


class TestSinRepresentantesRule:
    def test_triggers_when_no_representatives(self) -> None:
        company = Company()
        result = SinRepresentantesRule().evaluate(company)
        assert result is not None
        assert "representantes" in result.mensaje.lower()

    def test_not_triggered_with_representatives(self) -> None:
        company = Company(representatives=[{"name": "John"}])
        assert SinRepresentantesRule().evaluate(company) is None


class TestMultiplesActividadesPrincipalesRule:
    def test_triggers_with_multiple_principal(self) -> None:
        company = Company(activities=[
            Activity(codigo="011101", descripcion="CULTIVO", principal=True),
            Activity(codigo="012400", descripcion="FRUTAS", principal=True),
        ])
        result = MultiplesActividadesPrincipalesRule().evaluate(company)
        assert result is not None
        assert "principales" in result.mensaje.lower()

    def test_not_triggered_with_one_principal(self) -> None:
        company = Company(activities=[
            Activity(codigo="011101", descripcion="CULTIVO", principal=True),
            Activity(codigo="012400", descripcion="FRUTAS", principal=False),
        ])
        assert MultiplesActividadesPrincipalesRule().evaluate(company) is None

    def test_not_triggered_with_no_principal_flag(self) -> None:
        company = Company(activities=[
            Activity(codigo="011101", descripcion="CULTIVO", principal=False),
        ])
        assert MultiplesActividadesPrincipalesRule().evaluate(company) is None


class TestSinRegimenTributarioRule:
    def test_triggers_when_no_regimen(self) -> None:
        company = Company(contributor=Contributor(rut="12.345.678-9"))
        result = SinRegimenTributarioRule().evaluate(company)
        assert result is not None
        assert "régimen" in result.mensaje.lower()

    def test_not_triggered_with_regimen(self) -> None:
        company = Company(
            contributor=Contributor(regimen_tributario="REGIMEN PRO PYME GENERAL"),
        )
        assert SinRegimenTributarioRule().evaluate(company) is None

    def test_not_triggered_without_contributor(self) -> None:
        company = Company()
        assert SinRegimenTributarioRule().evaluate(company) is None


class TestRuleEngineOnCompany:
    def test_run_on_company_returns_results(self) -> None:
        engine = RuleEngine()
        engine.register(SinActividadesRule())
        engine.register(SinRepresentantesRule())
        company = Company()
        results = engine.run_on_company(company)
        assert len(results) == 2
        assert results[0].nombre == "Sin actividades económicas"
        assert results[1].nombre == "Sin representantes legales"

    def test_run_on_company_empty(self) -> None:
        engine = RuleEngine()
        company = Company(
            activities=[Activity(codigo="012400", descripcion="CULTIVO")],
            representatives=[{"name": "John"}],
        )
        results = engine.run_on_company(company)
        assert results == []
