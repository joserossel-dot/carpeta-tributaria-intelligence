from src.detectors.section_detector import SectionDetector
from src.extractors.pdf_extractor import PDFExtractor
from src.parsers.contributor_parser import ContributorParser


class TestContributorParser:
    def _parse(self, pdf_name: str):
        ex = PDFExtractor()
        sd = SectionDetector()
        parser = ContributorParser()
        extract_result = ex.extract(f"examples/{pdf_name}")
        section_result = sd.detect(extract_result)
        return parser.parse(extract_result, section_result)

    def test_gonzagri_ltda(self) -> None:
        c = self._parse("CPTAgrGonzagriLtda.pdf")
        assert c.rut == "79606270-3"
        assert c.razon_social == "AGRICOLA GONZAGRI LIMITADA"
        assert c.fecha_generacion == "30/01/2020 10:40"
        assert c.fecha_inicio_actividades is not None
        assert c.domicilio is not None
        assert c.comuna is not None
        assert c.tipo_contribuyente == "Primera categoría"
        assert c.regimen_tributario is None

    def test_gonzalez_ltda(self) -> None:
        c = self._parse("CPTAgrGonzalezLtda.pdf")
        assert c.rut == "77442850-K"
        assert c.razon_social == "AGRICOLA GONZALEZ LIMITADA"
        assert c.fecha_generacion == "30/01/2020 10:38"
        assert c.tipo_contribuyente == "Primera categoría"

    def test_exportadora(self) -> None:
        c = self._parse("CPTExportadora.pdf")
        assert c.rut == "99556090-9"
        assert c.razon_social == "EXPORTADORA GONZAGRI S A"
        assert c.fecha_generacion == "30/01/2020 10:35"

    def test_clinica_hyperbaric(self) -> None:
        c = self._parse("Carpeta Tributaria.CLINICA HYPERBARIC.pdf")
        assert c.rut == "77460385-9"
        assert c.razon_social == "CLINICA HYPERBARIC SPA"
        assert c.fecha_generacion == "02/06/2026 10:31"
        assert c.fecha_inicio_actividades == "28/01/2022"
        assert c.tipo_contribuyente == "Primera Categoría"
        assert c.regimen_tributario is not None
        assert "REGIMEN PRO PYME" in (c.regimen_tributario or "")

    def test_proterm_sa(self) -> None:
        c = self._parse("Carpeta_Tributaria_Regular (4).pdf")
        assert c.rut == "78155540-1"
        assert c.razon_social == "PROTERM S.A."
        assert c.fecha_generacion == "03/06/2026 18:39"
        assert c.tipo_contribuyente == "Primera Categoría"

    def test_pdf_sin_datos_no_crash(self) -> None:
        from src.models.extract_result import ExtractResult, PageResult
        from src.models.section_result import SectionResult

        parser = ContributorParser()
        result = parser.parse(
            ExtractResult(pages=[PageResult(page=1, text="texto sin datos")]),
            SectionResult(secciones={}),
        )
        assert result.rut is None
