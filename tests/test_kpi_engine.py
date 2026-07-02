from datetime import datetime

from src.kpis.kpi_engine import KPIEngine
from src.kpis.kpi_result import KPIResult
from src.models.activity import Activity
from src.models.contributor import Contributor
from src.models.f29 import F29
from src.models.tax_folder import Metadata, TaxFolder


class TestKPIEngine:
    def test_empty_tax_folder(self) -> None:
        tf = TaxFolder(
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        result = KPIEngine().calculate(tf)
        assert isinstance(result, KPIResult)
        assert result.activity_count == 0
        assert result.f29_count == 0
        assert result.representative_count == 0
        assert result.property_count == 0
        assert result.vehicle_count == 0
        assert result.principal_activity is None
        assert result.first_f29_period is None
        assert result.last_f29_period is None
        assert result.declared_months is None
        assert result.company_age_years is None
        assert isinstance(result.processing_timestamp, str)

    def test_with_data(self) -> None:
        tf = TaxFolder(
            activities=[
                Activity(codigo="012400", descripcion="CULTIVO", principal=True),
            ],
            f29=[
                F29(periodo="2024-01", folio="1", detalles=[], fecha_presentacion=None),
                F29(periodo="2024-02", folio="2", detalles=[], fecha_presentacion=None),
            ],
            representatives=[{"name": "A"}],
            properties=[{"address": "B"}],
            vehicles=[{"plate": "C"}],
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        result = KPIEngine().calculate(tf)
        assert result.activity_count == 1
        assert result.principal_activity == "CULTIVO"
        assert result.f29_count == 2
        assert result.first_f29_period == "2024-01"
        assert result.last_f29_period == "2024-02"
        assert result.declared_months == 2
        assert result.representative_count == 1
        assert result.property_count == 1
        assert result.vehicle_count == 1
        assert result.company_age_years is None  # no contributor

    def test_principal_activity_fallback(self) -> None:
        tf = TaxFolder(
            activities=[
                Activity(codigo="012400", descripcion="FIRST", principal=False),
                Activity(codigo="012600", descripcion="SECOND", principal=False),
            ],
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        result = KPIEngine().calculate(tf)
        assert result.principal_activity == "FIRST"

    def test_company_age_from_date(self) -> None:
        tf = TaxFolder(
            contributor=Contributor(fecha_inicio_actividades="01/01/2020"),
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        result = KPIEngine().calculate(tf)
        assert result.company_age_years is not None
        assert result.company_age_years > 6.0  # 2020-2026

    def test_company_age_returns_none_for_invalid_date(self) -> None:
        tf = TaxFolder(
            contributor=Contributor(fecha_inicio_actividades="not-a-date"),
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        result = KPIEngine().calculate(tf)
        assert result.company_age_years is None

    def test_company_age_returns_none_for_missing_date(self) -> None:
        tf = TaxFolder(
            contributor=Contributor(),
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        result = KPIEngine().calculate(tf)
        assert result.company_age_years is None

    def test_no_f29_returns_none_periods(self) -> None:
        tf = TaxFolder(
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        result = KPIEngine().calculate(tf)
        assert result.first_f29_period is None
        assert result.last_f29_period is None
        assert result.declared_months is None

    def test_kpis_in_tax_folder_model(self) -> None:
        from src.core.tax_folder_engine import TaxFolderEngine

        engine = TaxFolderEngine("examples/CPTExportadora.pdf")
        result = engine.parse()
        assert result.kpis is not None
        assert result.kpis.activity_count >= 1
        assert result.kpis.f29_count >= 1

    def test_kpis_in_model_dump(self) -> None:
        from src.core.tax_folder_engine import TaxFolderEngine

        engine = TaxFolderEngine("examples/CPTExportadora.pdf")
        result = engine.parse()
        dumped = result.model_dump()
        assert "kpis" in dumped
        assert dumped["kpis"] is not None

    def test_multiple_activities_no_principal_flag(self) -> None:
        tf = TaxFolder(
            activities=[
                Activity(codigo="012400", descripcion="FIRST", principal=False),
            ],
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        result = KPIEngine().calculate(tf)
        assert result.principal_activity == "FIRST"

    def test_timestamp_is_set(self) -> None:
        tf = TaxFolder(
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        result = KPIEngine().calculate(tf)
        assert result.processing_timestamp != ""
