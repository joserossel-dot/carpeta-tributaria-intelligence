from src.models.annual_tax_return import AnnualTaxReturn
from src.models.extract_result import ExtractResult, PageResult
from src.models.section_result import SectionResult
from src.parsers.f22_parser import F22Parser


class TestF22Parser:
    def _make_f22_page(self, anio: str, codigos: list[tuple[str, str, str]]) -> str:
        lines = [
            f"REPUBLICA DE CHILE AÑO TRIBUTARIO {anio} 07N° 123456",
            "INTERNOS FORM. 22 IMPUESTOS ANUALES A LA RENTA",
        ]
        for codigo, glosa, valor in codigos:
            lines.append(f"{codigo} {glosa} {valor}")
        return "\n".join(lines)

    def _parse(self, pages_text: list[str]) -> list[AnnualTaxReturn]:
        parser = F22Parser()
        pages = [PageResult(page=i + 1, text=t) for i, t in enumerate(pages_text)]
        extract = ExtractResult(pages=pages)
        sections = SectionResult(secciones={"FORMULARIO 22": list(range(1, len(pages) + 1))})
        return parser.parse(extract, sections)

    def test_single_form(self) -> None:
        text = self._make_f22_page("2024", [
            ("1657", "Ingresos del giro percibidos o devengados", "100000000"),
            ("1694", "Renta líquida imponible afecta a IDPC del ejercicio", "30000000"),
            ("844", "Capital propio tributario", "50000000"),
            ("305", "RESULTADO LIQUIDACIÓN ANUAL IMPUESTO A LA RENTA", "5000000"),
            ("36", "PPM y remanente del IEAM", "2000000"),
            ("82", "Crédito por gastos de capacitación", "500000"),
            ("1109", "Base Imponible de créditos", "30000000"),
        ])
        result = self._parse([text])
        assert len(result) == 1
        r = result[0]
        assert r.anio_tributario == "2024"
        assert r.ingresos == 100000000
        assert r.renta_liquida_imponible == 30000000
        assert r.capital_propio_tributario == 50000000
        assert r.impuesto_determinado == 5000000
        assert r.ppm == 2000000
        assert r.creditos == 500000
        assert r.base_imponible == 30000000
        assert r.resultado_tributario is None
        assert r.perdidas is None

    def test_multiple_forms_sorted(self) -> None:
        text_2024 = self._make_f22_page("2024", [("1657", "Ingresos", "100000")])
        text_2025 = self._make_f22_page("2025", [("1657", "Ingresos", "200000")])
        # 2025 page comes first
        result = self._parse([text_2025, text_2024])
        assert len(result) == 2
        assert result[0].anio_tributario == "2025"
        assert result[1].anio_tributario == "2024"
        assert result[0].ingresos == 200000
        assert result[1].ingresos == 100000

    def test_missing_fields(self) -> None:
        text = self._make_f22_page("2024", [("1657", "Ingresos", "50000")])
        result = self._parse([text])
        r = result[0]
        assert r.ingresos == 50000
        assert r.renta_liquida_imponible is None
        assert r.ppm is None
        assert "No se encontró Capital Propio Tributario" in r.observaciones

    def test_negative_resultado(self) -> None:
        text = self._make_f22_page("2024", [
            ("1657", "Ingresos", "100000"),
            ("305", "RESULTADO LIQUIDACIÓN ANUAL IMPUESTO A LA RENTA", "-14489795"),
        ])
        result = self._parse([text])
        r = result[0]
        assert r.impuesto_determinado == -14489795

    def test_no_f22_section_returns_empty(self) -> None:
        parser = F22Parser()
        extract = ExtractResult(pages=[PageResult(page=1, text="no f22")])
        sections = SectionResult(secciones={})
        result = parser.parse(extract, sections)
        assert result == []

    def test_cpt_positive_vs_844(self) -> None:
        text = self._make_f22_page("2024", [
            ("844", "Capital propio tributario", "50000000"),
            ("645", "CPT positivo final", "60000000"),
        ])
        result = self._parse([text])
        r = result[0]
        # 844 takes priority
        assert r.capital_propio_tributario == 50000000

    def test_anio_tributario_spanish_n(self) -> None:
        text = self._make_f22_page("2025", [("1657", "Ingresos", "100000")])
        text_con_n = text.replace("AÑO", "ANO")
        result = self._parse([text_con_n])
        assert len(result) == 1
        assert result[0].anio_tributario == "2025"

    def test_page_range_includes_continuation(self) -> None:
        parser = F22Parser()
        page1 = (
            "Declaraciones de Renta - Formulario 22 (F22)\n"
            "REPUBLICA DE CHILE AÑO TRIBUTARIO 2024 07N° 123\n"
            "INTERNOS FORM. 22 IMPUESTOS ANUALES A LA RENTA\n"
            "1657 Ingresos del giro 100000 36 PPM del IEAM 20000\n"
        )
        page2 = (
            "1694 Renta líquida imponible 30000 844 Capital propio tributario 50000\n"
            "305 RESULTADO LIQUIDACIÓN 5000\n"
        )
        pages = [PageResult(page=1, text=page1), PageResult(page=2, text=page2)]
        extract = ExtractResult(pages=pages)
        sections = SectionResult(secciones={"FORMULARIO 22": [1]})
        result = parser.parse(extract, sections)
        assert len(result) == 1
        r = result[0]
        assert r.ingresos == 100000
        assert r.renta_liquida_imponible == 30000
        assert r.capital_propio_tributario == 50000
        assert r.impuesto_determinado == 5000
        assert r.ppm == 20000
