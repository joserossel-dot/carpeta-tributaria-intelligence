from pathlib import Path

from src.detectors.section_detector import SectionDetector
from src.extractors.pdf_extractor import PDFExtractor
from src.parsers.f22_parser import F22Parser


class TestF22ParserIntegration:
    def _get_f22(self, pdf_name: str) -> list | None:
        path = f"examples/{pdf_name}"
        if not Path(path).exists():
            return None
        ex = PDFExtractor()
        sd = SectionDetector()
        parser = F22Parser()
        r = ex.extract(path)
        s = sd.detect(r)
        return parser.parse(r, s)

    def test_proterm_has_forms(self) -> None:
        forms = self._get_f22("Carpeta_Tributaria_Regular (4).pdf")
        assert forms is not None
        assert len(forms) >= 3  # AT 2026, 2025, 2024

    def test_proterm_2026_values(self) -> None:
        forms = self._get_f22("Carpeta_Tributaria_Regular (4).pdf")
        assert forms is not None
        at26 = next((f for f in forms if f.anio_tributario == "2026"), None)
        assert at26 is not None
        assert at26.ingresos is not None
        assert at26.ingresos > 0
        assert at26.renta_liquida_imponible is not None
        assert at26.renta_liquida_imponible > 0
        assert at26.ppm is not None
        assert at26.impuesto_determinado is not None

    def test_proterm_2025_values(self) -> None:
        forms = self._get_f22("Carpeta_Tributaria_Regular (4).pdf")
        assert forms is not None
        at25 = next((f for f in forms if f.anio_tributario == "2025"), None)
        assert at25 is not None
        assert at25.ingresos is not None
        assert at25.ingresos > 0
        assert at25.renta_liquida_imponible is not None
        assert at25.creditos is not None

    def test_proterm_2024_values(self) -> None:
        forms = self._get_f22("Carpeta_Tributaria_Regular (4).pdf")
        assert forms is not None
        at24 = next((f for f in forms if f.anio_tributario == "2024"), None)
        assert at24 is not None
        assert at24.ingresos is not None
        assert at24.ingresos > 0

    def test_proterm_chronological(self) -> None:
        forms = self._get_f22("Carpeta_Tributaria_Regular (4).pdf")
        assert forms is not None
        anios = [f.anio_tributario for f in forms]
        assert anios == sorted(anios, reverse=True)  # newest first

    def test_gonzagri_no_declaration(self) -> None:
        forms = self._get_f22("CPTAgrGonzagriLtda.pdf")
        assert forms is not None
        for f in forms:
            assert f.ingresos is None
            assert "No se encontraron Ingresos del Giro" in f.observaciones

    def test_gonzalez_no_declaration(self) -> None:
        forms = self._get_f22("CPTAgrGonzalezLtda.pdf")
        assert forms is not None
        for f in forms:
            assert f.ingresos is None

    def test_exportadora_no_declaration(self) -> None:
        forms = self._get_f22("CPTExportadora.pdf")
        assert forms is not None
        for f in forms:
            assert f.ingresos is None

    def test_clinica_no_declaration(self) -> None:
        forms = self._get_f22("Carpeta Tributaria.CLINICA HYPERBARIC.pdf")
        assert forms is not None
        for f in forms:
            assert f.ingresos is None

    def test_gonzagri_sa_no_declaration(self) -> None:
        forms = self._get_f22("CPTGonzagriS.A..pdf")
        assert forms is not None
        for f in forms:
            assert f.ingresos is None

    def test_proterm_ingresos_specific(self) -> None:
        forms = self._get_f22("Carpeta_Tributaria_Regular (4).pdf")
        assert forms is not None
        at26 = next((f for f in forms if f.anio_tributario == "2026"), None)
        assert at26 is not None
        # Known values from the PDF: 1657 = 6398884318
        assert at26.ingresos == 6398884318

    def test_proterm_cpt_specific(self) -> None:
        forms = self._get_f22("Carpeta_Tributaria_Regular (4).pdf")
        assert forms is not None
        at26 = next((f for f in forms if f.anio_tributario == "2026"), None)
        assert at26 is not None
        # Known: 844 = 102644484
        assert at26.capital_propio_tributario == 102644484

    def test_proterm_ppm_specific(self) -> None:
        forms = self._get_f22("Carpeta_Tributaria_Regular (4).pdf")
        assert forms is not None
        at26 = next((f for f in forms if f.anio_tributario == "2026"), None)
        assert at26 is not None
        # Known: 36 = 233623721
        assert at26.ppm == 233623721
