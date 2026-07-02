from datetime import datetime

from src.kpis.kpi_result import KPIResult
from src.models.activity import Activity
from src.models.tax_folder import TaxFolder


class KPIEngine:
    def calculate(self, tax_folder: TaxFolder) -> KPIResult:
        activity_count = len(tax_folder.activities)
        principal_activity = self._get_principal_activity(tax_folder.activities)
        f29_count = len(tax_folder.f29)
        periods = self._get_f29_periods(tax_folder)

        return KPIResult(
            company_age_years=self._compute_company_age(tax_folder),
            activity_count=activity_count,
            principal_activity=principal_activity,
            representative_count=len(tax_folder.representatives),
            property_count=len(tax_folder.properties),
            vehicle_count=len(tax_folder.vehicles),
            f29_count=f29_count,
            first_f29_period=periods[0] if periods else None,
            last_f29_period=periods[-1] if periods else None,
            declared_months=self._count_declared_months(periods),
            processing_timestamp=datetime.now().isoformat(),
        )

    @staticmethod
    def _get_principal_activity(activities: list) -> str | None:
        for a in activities:
            if isinstance(a, Activity) and a.principal and a.descripcion:
                return a.descripcion
        if activities:
            first = activities[0]
            if isinstance(first, Activity) and first.descripcion:
                return first.descripcion
        return None

    @staticmethod
    def _get_f29_periods(tax_folder: TaxFolder) -> list[str]:
        try:
            periods = sorted(
                (f.periodo for f in tax_folder.f29 if f and f.periodo),
                key=lambda p: p,
            )
            return periods
        except Exception:
            return []

    @staticmethod
    def _count_declared_months(periods: list[str]) -> int | None:
        if not periods:
            return None
        return len(periods)

    @staticmethod
    def _compute_company_age(tax_folder: TaxFolder) -> float | None:
        if (
            not tax_folder.contributor
            or not tax_folder.contributor.fecha_inicio_actividades
        ):
            return None
        raw = tax_folder.contributor.fecha_inicio_actividades
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                start = datetime.strptime(raw, fmt)
                return round((datetime.now() - start).days / 365.25, 1)
            except (ValueError, TypeError):
                continue
        return None
