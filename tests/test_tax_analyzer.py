from src.analyzers.analysis_result import AnalysisResult
from src.analyzers.tax_analyzer import TaxAnalyzer
from src.kpis.kpi_result import KPIResult
from src.models.activity import Activity
from src.models.company import Company
from src.models.f29 import F29


class TestTaxAnalyzer:
    def test_empty_company_triggers_rules(self) -> None:
        company = Company()
        result = TaxAnalyzer().analyze(company)
        assert isinstance(result, AnalysisResult)
        assert len(result.alerts) == 2
        assert len(result.warnings) == 1
        assert any("actividades" in a for a in result.alerts)
        assert any("F29" in a for a in result.alerts)
        assert any("representantes" in w for w in result.warnings)

    def test_with_data_suppresses_rules(self) -> None:
        company = Company(
            activities=[Activity(codigo="012400", descripcion="CULTIVO", principal=True)],
            f29=[F29(periodo="2024-01", folio="1", detalles=[])],
            representatives=[{"name": "John"}],
            properties=[{"address": "Santiago"}],
            vehicles=[{"plate": "ABC123"}],
            kpis=KPIResult(
                activity_count=1,
                f29_count=1,
                representative_count=1,
                property_count=1,
                vehicle_count=1,
            ),
        )
        result = TaxAnalyzer().analyze(company)
        assert result.statistics["total_actividades"] == 1
        assert result.statistics["total_f29"] == 1
        assert result.statistics["total_representantes"] == 1
        assert result.statistics["total_propiedades"] == 1
        assert result.statistics["total_vehiculos"] == 1
        assert result.alerts == []
        assert result.warnings == []

    def test_analysis_in_tax_folder_model(self) -> None:
        from src.models.tax_folder import Metadata, TaxFolder

        tf = TaxFolder(
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        assert hasattr(tf, "analysis")
        assert tf.analysis is None

    def test_engine_populates_analysis(self) -> None:
        from src.core.tax_folder_engine import TaxFolderEngine

        engine = TaxFolderEngine("examples/CPTExportadora.pdf")
        result = engine.parse()
        assert result.analysis is not None
        assert result.analysis.statistics["total_actividades"] >= 1
        assert result.analysis.statistics["total_f29"] >= 1

    def test_analysis_in_model_dump(self) -> None:
        from src.core.tax_folder_engine import TaxFolderEngine

        engine = TaxFolderEngine("examples/CPTExportadora.pdf")
        result = engine.parse()
        dumped = result.model_dump()
        assert "analysis" in dumped
        assert dumped["analysis"] is not None
        assert "statistics" in dumped["analysis"]
