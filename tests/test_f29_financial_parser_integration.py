from pathlib import Path

from src.detectors.section_detector import SectionDetector
from src.extractors.pdf_extractor import PDFExtractor
from src.parsers.f29_financial_parser import F29FinancialParser
from src.parsers.f29_parser import F29Parser


class TestF29FinancialParserIntegration:
    def _get_monthly(self, pdf_name: str):
        path = f"examples/{pdf_name}"
        if not Path(path).exists():
            return None
        ex = PDFExtractor()
        sd = SectionDetector()
        parser = F29Parser()
        fin_parser = F29FinancialParser()
        r = ex.extract(path)
        s = sd.detect(r)
        f29s = parser.parse(r, s)
        return fin_parser.parse(f29s)

    def test_gonzagri_ltda_periods(self) -> None:
        monthly = self._get_monthly("CPTAgrGonzagriLtda.pdf")
        assert monthly is not None
        assert len(monthly) >= 30
        assert monthly[0].periodo == "2017-02"
        assert monthly[-1].periodo == "2019-12"
        for m in monthly:
            assert m.periodo
            if m.compras is not None:
                assert m.compras > 0

    def test_gonzagri_ltda_chronological(self) -> None:
        monthly = self._get_monthly("CPTAgrGonzagriLtda.pdf")
        assert monthly is not None
        periods = [m.periodo for m in monthly]
        assert periods == sorted(periods)

    def test_gonzagri_ltda_montos(self) -> None:
        monthly = self._get_monthly("CPTAgrGonzagriLtda.pdf")
        assert monthly is not None
        # spot-check a known period
        m = next((x for x in monthly if x.periodo == "2019-12"), None)
        assert m is not None
        assert m.ventas_afectas is not None
        assert m.total_ventas is not None
        assert m.total_ventas >= m.ventas_afectas

    def test_exportadora_periods(self) -> None:
        monthly = self._get_monthly("CPTExportadora.pdf")
        assert monthly is not None
        assert len(monthly) >= 30
        assert monthly[0].periodo == "2017-02"
        assert monthly[-1].periodo == "2019-12"

    def test_gonzalez_ltda_periods(self) -> None:
        monthly = self._get_monthly("CPTAgrGonzalezLtda.pdf")
        assert monthly is not None
        assert len(monthly) >= 30

    def test_clinica_hyperbaric(self) -> None:
        monthly = self._get_monthly("Carpeta Tributaria.CLINICA HYPERBARIC.pdf")
        assert monthly is not None
        assert len(monthly) >= 30
        assert monthly[0].periodo <= "2023-06"
        assert monthly[-1].periodo == "2026-04"

    def test_total_ventas_consistency(self) -> None:
        monthly = self._get_monthly("CPTAgrGonzagriLtda.pdf")
        assert monthly is not None
        for m in monthly:
            if m.total_ventas is not None:
                partes = [v for v in [m.ventas_afectas, m.ventas_exentas, m.ventas_exportacion] if v is not None]
                expected = sum(partes)
                assert m.total_ventas == expected, (
                    f"Periodo {m.periodo}: total_ventas={m.total_ventas} != suma={expected}"
                )

    def test_all_valid_pdfs(self) -> None:
        valid = [
            "CPTAgrGonzagriLtda.pdf",
            "CPTAgrGonzalezLtda.pdf",
            "CPTExportadora.pdf",
        ]
        for pdf in valid:
            monthly = self._get_monthly(pdf)
            assert monthly is not None, f"Failed for {pdf}"
            assert len(monthly) > 0, f"No monthly data for {pdf}"
