import re
from typing import Pattern

from src.models.extract_result import ExtractResult
from src.models.section_result import SectionResult


class SectionDetector:
    """Detecta en qué páginas aparece cada sección dentro de un ExtractResult.

    Usa expresiones regulares para buscar encabezados de sección
    sin interpretar el contenido del documento.
    """

    SECTIONS: dict[str, Pattern[str]] = {
        "IDENTIFICACION DEL CONTRIBUYENTE": re.compile(
            r"IDENTIFICACION\s+DEL\s+CONTRIBUYENTE", re.IGNORECASE
        ),
        "REPRESENTANTES LEGALES": re.compile(
            r"REPRESENTANTE(?:S)?\s+LEGAL(?:ES)?", re.IGNORECASE
        ),
        "ACTIVIDADES ECONOMICAS": re.compile(
            r"ACTIVIDAD(?:ES)?\s+ECON[ÓO]?MICA(?:S)?", re.IGNORECASE
        ),
        "FORMULARIO 29": re.compile(
            r"FORMULARIO\s+29|F29", re.IGNORECASE
        ),
        "FORMULARIO 22": re.compile(
            r"FORMULARIO\s+22|FORM\.\s*22|F22", re.IGNORECASE
        ),
        "DECLARACIONES JURADAS": re.compile(
            r"DECLARACION(?:ES)?\s+JURADA(?:S)?", re.IGNORECASE
        ),
        "BIENES RAICES": re.compile(
            r"BIENES\s+RA(?:Í|I)CE(?:S)?", re.IGNORECASE
        ),
        "VEHICULOS": re.compile(
            r"VEH(?:Í|I)CULO(?:S)?", re.IGNORECASE
        ),
        "CONFORMACION DE LA SOCIEDAD": re.compile(
            r"CONFORMACION\s+DE\s+LA\s+SOCIEDAD", re.IGNORECASE
        ),
    }

    def detect(self, result: ExtractResult) -> SectionResult:
        """Analiza todas las páginas y detecta en cuáles aparece cada sección.

        Args:
            result: ExtractResult con el texto extraído del PDF.

        Returns:
            SectionResult con un dict que mapea nombre de sección
            a lista de números de página donde fue encontrada.
        """
        secciones: dict[str, list[int]] = {name: [] for name in self.SECTIONS}

        for page in result.pages:
            for section_name, pattern in self.SECTIONS.items():
                if pattern.search(page.text):
                    secciones[section_name].append(page.page)

        return SectionResult(secciones=secciones)
