from abc import ABC

from src.models.company import Company
from src.models.tax_folder import TaxFolder
from src.rules.rule_result import RuleResult
from src.rules.validation_result import ValidationResult


class BaseRule(ABC):
    def check(self, tax_folder: TaxFolder) -> ValidationResult | None:
        return None

    def evaluate(self, company: Company) -> RuleResult | None:
        return None
