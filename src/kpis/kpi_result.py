from datetime import datetime

from pydantic import BaseModel


class KPIResult(BaseModel):
    company_age_years: float | None = None
    activity_count: int = 0
    principal_activity: str | None = None
    representative_count: int = 0
    property_count: int = 0
    vehicle_count: int = 0
    f29_count: int = 0
    first_f29_period: str | None = None
    last_f29_period: str | None = None
    declared_months: int | None = None
    processing_timestamp: str = ""
