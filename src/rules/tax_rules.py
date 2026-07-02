from src.models.company import Company
from src.rules.base_rule import BaseRule
from src.rules.rule_result import RuleResult


class SinActividadesRule(BaseRule):
    def evaluate(self, company: Company) -> RuleResult | None:
        if not company.activities:
            return RuleResult(
                nombre="Sin actividades económicas",
                severidad="error",
                mensaje="La empresa no tiene actividades económicas registradas.",
                categoria="ACTIVIDADES",
                recomendado="Registrar al menos una actividad económica en el SII.",
            )
        return None


class SinF29Rule(BaseRule):
    def evaluate(self, company: Company) -> RuleResult | None:
        if not company.f29:
            return RuleResult(
                nombre="Sin declaraciones F29",
                severidad="error",
                mensaje="La empresa no tiene declaraciones F29 registradas.",
                categoria="F29",
                recomendado="Verificar si la empresa ha presentado declaraciones mensuales.",
            )
        return None


class SinRepresentantesRule(BaseRule):
    def evaluate(self, company: Company) -> RuleResult | None:
        if not company.representatives:
            return RuleResult(
                nombre="Sin representantes legales",
                severidad="warning",
                mensaje="La empresa no tiene representantes legales registrados.",
                categoria="REPRESENTANTES",
                recomendado="Registrar al menos un representante legal en el SII.",
            )
        return None


class MultiplesActividadesPrincipalesRule(BaseRule):
    def evaluate(self, company: Company) -> RuleResult | None:
        principales = [a for a in company.activities if a.principal]
        if len(principales) > 1:
            codigos = ", ".join(a.codigo for a in principales)
            return RuleResult(
                nombre="Múltiples actividades principales",
                severidad="warning",
                mensaje=f"Se detectaron {len(principales)} actividades principales: {codigos}.",
                categoria="ACTIVIDADES",
                recomendado="Revisar y definir una única actividad principal en el SII.",
            )
        return None


class SinRegimenTributarioRule(BaseRule):
    def evaluate(self, company: Company) -> RuleResult | None:
        if company.contributor and not company.contributor.regimen_tributario:
            return RuleResult(
                nombre="Sin régimen tributario",
                severidad="error",
                mensaje="La empresa no tiene régimen tributario registrado.",
                categoria="CONTRIBUYENTE",
                recomendado="Verificar el régimen tributario asignado por el SII.",
            )
        return None
