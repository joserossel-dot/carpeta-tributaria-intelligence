from src.extractors.pdf_extractor import PDFExtractor
from src.detectors.section_detector import SectionDetector
from src.models.extract_result import ExtractResult, PageResult
from src.models.section_result import SectionResult
from src.parsers.economic_activities_parser import EconomicActivitiesParser


class TestEconomicActivitiesParser:
    def _parse(self, pdf_path: str) -> "list":
        ex = PDFExtractor()
        sd = SectionDetector()
        parser = EconomicActivitiesParser()
        extract_result = ex.extract(pdf_path)
        section_result = sd.detect(extract_result)
        return parser.parse(extract_result, section_result)

    def test_gonzagri_ltda_old_format(self) -> None:
        activities = self._parse("examples/CPTAgrGonzagriLtda.pdf")
        assert len(activities) == 3
        assert activities[0].codigo == "012400"
        assert activities[0].descripcion == "CULTIVO DE FRUTAS DE PEPITA Y DE HUESO"
        assert activities[0].principal is True
        assert activities[0].categoria is None
        assert activities[0].fecha_inicio is None

    def test_gonzalez_ltda_single_activity(self) -> None:
        activities = self._parse("examples/CPTAgrGonzalezLtda.pdf")
        assert len(activities) == 1
        assert activities[0].codigo == "016100"
        assert activities[0].principal is True

    def test_exportadora_single_activity(self) -> None:
        activities = self._parse("examples/CPTExportadora.pdf")
        assert len(activities) == 1
        assert activities[0].codigo == "461001"

    def test_gonzagri_sa_with_continuation(self) -> None:
        activities = self._parse("examples/CPTGonzagriS.A..pdf")
        assert len(activities) == 1
        assert activities[0].codigo == "681012"
        assert "INMUEBLES" in activities[0].descripcion
        assert activities[0].principal is True

    def test_clinica_hyperbaric_new_format(self) -> None:
        activities = self._parse("examples/Carpeta Tributaria.CLINICA HYPERBARIC.pdf")
        assert len(activities) == 1
        assert activities[0].codigo == "862021"
        assert "AMBULATORIA" in activities[0].descripcion
        assert activities[0].principal is True
        assert activities[0].categoria == "Primera Categoría"
        assert activities[0].fecha_inicio == "28/01/2022"

    def test_no_activities_section(self) -> None:
        parser = EconomicActivitiesParser()
        result = parser.parse(
            ExtractResult(pages=[PageResult(page=1, text="No activities here")]),
            SectionResult(secciones={}),
        )
        assert result == []

    def test_section_not_on_listed_page(self) -> None:
        parser = EconomicActivitiesParser()
        extract = ExtractResult(pages=[PageResult(page=1, text="Actividades Económicas: test\n")])
        section = SectionResult(secciones={"ACTIVIDADES ECONOMICAS": [5]})
        result = parser.parse(extract, section)
        assert result == []

    def test_section_missing_after_boundary(self) -> None:
        parser = EconomicActivitiesParser()
        extract = ExtractResult(pages=[PageResult(page=1, text="DATOS GENERALES\nCategoría Tributaria: Primera\n")])
        section = SectionResult(secciones={"ACTIVIDADES ECONOMICAS": [1]})
        result = parser.parse(extract, section)
        assert result == []
