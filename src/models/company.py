from pydantic import BaseModel

from src.analyzers.analysis_result import AnalysisResult
from src.kpis.kpi_result import KPIResult
from src.models.activity import Activity
from src.models.contributor import Contributor
from src.models.annual_tax_return import AnnualTaxReturn
from src.models.f29 import F29
from src.models.monthly_tax import MonthlyTax
from src.services.monthly_tax_service import MonthlyTaxResult


class Company(BaseModel):
    contributor: Contributor | None = None
    activities: list[Activity] = []
    representatives: list = []
    properties: list = []
    vehicles: list = []
    f29: list[F29] = []
    f22: list[AnnualTaxReturn] = []
    kpis: KPIResult | None = None
    analysis: AnalysisResult | None = None
    monthly_taxes: list[MonthlyTax] = []
    monthly_analysis: MonthlyTaxResult | None = None
