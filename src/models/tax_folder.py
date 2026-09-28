from pydantic import BaseModel

from src.analyzers.analysis_result import AnalysisResult
from src.kpis.kpi_result import KPIResult
from src.models.annual_tax_return import AnnualTaxReturn
from src.models.contributor import Contributor
from src.models.corporate import CorporateInfo
from src.models.credit_risk import CreditRiskResult
from src.models.f29 import F29
from src.models.monthly_tax import MonthlyTax
from src.rules.validation_result import ValidationResult
from src.services.monthly_tax_service import MonthlyTaxResult


class Metadata(BaseModel):
    source_file: str
    pages: int
    processing_time: float


class TaxFolder(BaseModel):
    contributor: Contributor | None = None
    representatives: list = []
    activities: list = []
    f29: list[F29] = []
    f22: list[AnnualTaxReturn] = []
    properties: list = []
    vehicles: list = []
    validation: list[ValidationResult] = []
    kpis: KPIResult | None = None
    analysis: AnalysisResult | None = None
    monthly_taxes: list[MonthlyTax] = []
    monthly_analysis: MonthlyTaxResult | None = None
    corporate: CorporateInfo | None = None
    credit_risk: CreditRiskResult | None = None
    metadata: Metadata

    @property
    def corporate_info(self) -> CorporateInfo | None:
        return self.corporate

