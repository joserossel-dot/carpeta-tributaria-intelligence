from src.analyzers.analysis_result import AnalysisResult
from src.kpis.kpi_result import KPIResult
from src.models.company import Company
from src.rules.rule_engine import RuleEngine
from src.rules.tax_rules import (
    MultiplesActividadesPrincipalesRule,
    SinActividadesRule,
    SinF29Rule,
    SinRegimenTributarioRule,
    SinRepresentantesRule,
)


class TaxAnalyzer:
    def __init__(self) -> None:
        self._rule_engine = RuleEngine()
        self._rule_engine.register(SinActividadesRule())
        self._rule_engine.register(SinF29Rule())
        self._rule_engine.register(SinRepresentantesRule())
        self._rule_engine.register(MultiplesActividadesPrincipalesRule())
        self._rule_engine.register(SinRegimenTributarioRule())

    def analyze(self, company: Company) -> AnalysisResult:
        kpis = company.kpis or KPIResult()
        statistics = {
            "total_actividades": kpis.activity_count,
            "total_f29": kpis.f29_count,
            "total_representantes": kpis.representative_count,
            "total_propiedades": kpis.property_count,
            "total_vehiculos": kpis.vehicle_count,
        }

        rule_results = self._rule_engine.run_on_company(company)
        alerts = [r.mensaje for r in rule_results if r.severidad in ("error", "critical")]
        warnings = [r.mensaje for r in rule_results if r.severidad in ("info", "warning")]

        return AnalysisResult(
            statistics=statistics,
            alerts=alerts,
            warnings=warnings,
        )
