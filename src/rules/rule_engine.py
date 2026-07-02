from src.models.company import Company
from src.models.tax_folder import TaxFolder
from src.rules.base_rule import BaseRule
from src.rules.rule_result import RuleResult
from src.rules.validation_result import ValidationResult


class RuleEngine:
    def __init__(self) -> None:
        self._rules: list[BaseRule] = []

    def register(self, rule: BaseRule) -> None:
        self._rules.append(rule)

    def run(self, tax_folder: TaxFolder) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        for rule in self._rules:
            result = rule.check(tax_folder)
            if result is not None:
                results.append(result)
        return results

    def run_on_company(self, company: Company) -> list[RuleResult]:
        results: list[RuleResult] = []
        for rule in self._rules:
            result = rule.evaluate(company)
            if result is not None:
                results.append(result)
        return results
