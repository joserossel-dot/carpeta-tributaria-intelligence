from src.detectors.section_detector import SectionDetector
from src.extractors.pdf_extractor import PDFExtractor
from src.models.extract_result import ExtractResult, PageResult
from src.models.section_result import SectionResult
from src.parsers.f29_parser import F29Parser


class TestF29Parser:
    def _parse(self, pdf_name: str) -> list:
        ex = PDFExtractor()
        sd = SectionDetector()
        parser = F29Parser()
        r = ex.extract(f"examples/{pdf_name}")
        s = sd.detect(r)
        return parser.parse(r, s)

    def test_gonzagri_ltda(self) -> None:
        forms = self._parse("CPTAgrGonzagriLtda.pdf")
        assert len(forms) > 0
        f = forms[0]
        assert f.periodo == "2019-12"
        assert f.folio == "6904798236"
        assert f.fecha_presentacion == "28/01/2020"
        assert len(f.detalles) > 0
        assert any(d.codigo == "503" for d in f.detalles)

    def test_clinica_hyperbaric(self) -> None:
        forms = self._parse("Carpeta Tributaria.CLINICA HYPERBARIC.pdf")
        assert len(forms) > 0
        f = forms[0]
        assert f.periodo == "2026-04"
        assert f.folio == "9004371616"
        assert f.fecha_presentacion == "12/05/2026"
        assert len(f.detalles) > 0
        assert any(d.codigo == "586" for d in f.detalles)

    def test_multiple_forms(self) -> None:
        forms = self._parse("CPTAgrGonzagriLtda.pdf")
        assert len(forms) >= 30  # old format has ~35 F29 forms
        assert forms[0].periodo > forms[-1].periodo  # sorted desc

    def test_form_has_all_fields(self) -> None:
        forms = self._parse("CPTExportadora.pdf")
        f = forms[0]
        assert f.periodo
        assert f.folio
        assert f.detalles
        for d in f.detalles:
            assert d.codigo
            assert d.glosa
            assert d.valor

    def test_no_f29_pages_returns_empty(self) -> None:
        parser = F29Parser()
        result = parser.parse(
            ExtractResult(pages=[PageResult(page=1, text="sin datos")]),
            SectionResult(secciones={}),
        )
        assert result == []
