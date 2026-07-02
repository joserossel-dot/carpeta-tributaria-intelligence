from src.kpis.kpi_result import KPIResult
from src.mappers.tax_folder_mapper import TaxFolderMapper
from src.models.activity import Activity
from src.models.company import Company
from src.models.contributor import Contributor
from src.models.f29 import F29
from src.models.tax_folder import Metadata, TaxFolder


class TestTaxFolderMapper:
    def test_map_empty_tax_folder(self) -> None:
        tf = TaxFolder(
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        company = TaxFolderMapper().map(tf)
        assert isinstance(company, Company)
        assert company.contributor is None
        assert company.activities == []
        assert company.representatives == []
        assert company.properties == []
        assert company.vehicles == []
        assert company.f29 == []
        assert company.kpis is None
        assert company.analysis is None

    def test_map_full_tax_folder(self) -> None:
        kpis = KPIResult(activity_count=1, f29_count=2)
        tf = TaxFolder(
            contributor=Contributor(rut="12.345.678-9", razon_social="TEST SPA"),
            activities=[Activity(codigo="012400", descripcion="CULTIVO")],
            representatives=[{"name": "John"}],
            properties=[{"address": "St"}],
            vehicles=[{"plate": "ABC"}],
            f29=[
                F29(periodo="2024-01", folio="1", detalles=[]),
                F29(periodo="2024-02", folio="2", detalles=[]),
            ],
            kpis=kpis,
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        company = TaxFolderMapper().map(tf)
        assert company.contributor.rut == "12.345.678-9"
        assert company.contributor.razon_social == "TEST SPA"
        assert len(company.activities) == 1
        assert company.activities[0].codigo == "012400"
        assert len(company.representatives) == 1
        assert len(company.properties) == 1
        assert len(company.vehicles) == 1
        assert len(company.f29) == 2
        assert company.kpis.activity_count == 1
        assert company.kpis.f29_count == 2

    def test_map_preserves_kpis(self) -> None:
        kpis = KPIResult(activity_count=5, f29_count=10)
        tf = TaxFolder(
            kpis=kpis,
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        company = TaxFolderMapper().map(tf)
        assert company.kpis is tf.kpis
        assert company.kpis.activity_count == 5

    def test_map_via_engine(self) -> None:
        from src.core.tax_folder_engine import TaxFolderEngine

        engine = TaxFolderEngine("examples/CPTExportadora.pdf")
        result = engine.parse()
        company = TaxFolderMapper().map(result)
        assert company is not None
        assert company.kpis is not None
        assert len(company.f29) > 0
        assert company.analysis is not None
