from src.detectors.section_detector import SectionDetector
from src.models.extract_result import ExtractResult, PageResult


def _make_result(*texts: str) -> ExtractResult:
    return ExtractResult(
        pages=[PageResult(page=i + 1, text=t) for i, t in enumerate(texts)]
    )


class TestSectionDetector:
    def test_detect_single_section(self) -> None:
        result = _make_result(
            "INFORMACION GENERAL DEL CONTRIBUYENTE",
            "IDENTIFICACION DEL CONTRIBUYENTE\nRUT: 76.123.456-7",
            "OTROS DATOS",
        )
        detector = SectionDetector()
        section_result = detector.detect(result)
        assert section_result.secciones["IDENTIFICACION DEL CONTRIBUYENTE"] == [2]

    def test_detect_section_across_multiple_pages(self) -> None:
        result = _make_result(
            "FORMULARIO 29 - RESUMEN",
            "CONTINUA FORMULARIO 29",
            "OTRA SECCION",
        )
        detector = SectionDetector()
        section_result = detector.detect(result)
        assert section_result.secciones["FORMULARIO 29"] == [1, 2]

    def test_detect_all_known_sections(self) -> None:
        texts = [
            "IDENTIFICACION DEL CONTRIBUYENTE",
            "REPRESENTANTES LEGALES",
            "ACTIVIDADES ECONOMICAS",
            "FORMULARIO 29",
            "FORMULARIO 22",
            "DECLARACIONES JURADAS",
            "BIENES RAICES",
            "VEHICULOS",
            "CONFORMACION DE LA SOCIEDAD",
        ]
        result = _make_result(*texts)
        detector = SectionDetector()
        section_result = detector.detect(result)

        for i, section in enumerate(detector.SECTIONS, start=1):
            assert section_result.secciones[section] == [i], f"Fallo en {section}"

    def test_no_sections_found(self) -> None:
        result = _make_result(
            "Texto sin ninguna sección relevante",
            "Más contenido irrelevante",
        )
        detector = SectionDetector()
        section_result = detector.detect(result)

        for pages in section_result.secciones.values():
            assert pages == []

    def test_detect_with_variations(self) -> None:
        result = _make_result(
            "IDENTIFICACION DEL CONTRIBUYENTE",
            "REPRESENTANTE LEGAL",
            "ACTIVIDAD ECONOMICA",
            "FORMULARIO 29 - ADJUNTAR",
            "F22",
            "DECLARACION JURADA",
            "BIENES RAICES",
            "VEHICULO",
            "f29",
            "CONFORMACION DE LA SOCIEDAD",
        )
        detector = SectionDetector()
        section_result = detector.detect(result)

        assert section_result.secciones["IDENTIFICACION DEL CONTRIBUYENTE"] == [1]
        assert section_result.secciones["REPRESENTANTES LEGALES"] == [2]
        assert section_result.secciones["ACTIVIDADES ECONOMICAS"] == [3]
        assert section_result.secciones["FORMULARIO 29"] == [4, 9]
        assert section_result.secciones["FORMULARIO 22"] == [5]
        assert section_result.secciones["DECLARACIONES JURADAS"] == [6]
        assert section_result.secciones["BIENES RAICES"] == [7]
        assert section_result.secciones["VEHICULOS"] == [8]
        assert section_result.secciones["CONFORMACION DE LA SOCIEDAD"] == [10]

    def test_empty_text(self) -> None:
        result = _make_result("")
        detector = SectionDetector()
        section_result = detector.detect(result)

        for pages in section_result.secciones.values():
            assert pages == []
