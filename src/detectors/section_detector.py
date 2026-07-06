import re
from typing import Pattern

from src.models.extract_result import ExtractResult
from src.models.section_result import SectionResult


class SectionDetector:
    """Detecta en qué páginas aparece cada sección dentro de un ExtractResult.

    Usa expresiones regulares para buscar encabezados de sección
    sin interpretar el contenido del documento.
    """

    # NOTA: re.IGNORECASE NO pliega tildes (Ó != O para el motor de regex),
    # y el SII no es consistente entre carpetas al tildar encabezados.
    SECTIONS: dict[str, Pattern[str]] = {
        # El SII usa dos encabezados distintos para lo mismo segun la version
        # de carpeta: "Identificacion del Contribuyente" (formato viejo) y
        # "Datos del Contribuyente" (formato nuevo). Se detectan bajo la
        # misma clave para no alterar el conjunto de secciones conocidas.
        "IDENTIFICACION DEL CONTRIBUYENTE": re.compile(
            r"IDENTIFICACI[OÓ]N\s+DEL\s+CONTRIBUYENTE|DATOS\s+DEL\s+CONTRIBUYENTE",
            re.IGNORECASE,
        ),
        # Tolera "Representante Legal" y el formato real del SII
        # "Representante(s) Legal(es)" con parentesis literales.
        "REPRESENTANTES LEGALES": re.compile(
            r"REPRESENTANTE(?:\(?S\)?)?\s+LEGAL(?:\(?ES\)?)?", re.IGNORECASE
        ),
        "ACTIVIDADES ECONOMICAS": re.compile(
            r"ACTIVIDAD(?:ES)?\s+ECON[OÓ]MICA(?:S)?", re.IGNORECASE
        ),
        "FORMULARIO 29": re.compile(
            r"FORMULARIO\s+29|F29", re.IGNORECASE
        ),
        "FORMULARIO 22": re.compile(
            r"FORMULARIO\s+22|FORM\.\s*22|F22", re.IGNORECASE
        ),
        "DECLARACIONES JURADAS": re.compile(
            r"DECLARACI[OÓ]N(?:ES)?\s+JURADA(?:S)?", re.IGNORECASE
        ),
        "BIENES RAICES": re.compile(
            r"BIENES\s+RA[IÍ]CE(?:S)?", re.IGNORECASE
        ),
        "VEHICULOS": re.compile(
            r"VEH[IÍ]CULO(?:S)?", re.IGNORECASE
        ),
        "CONFORMACION DE LA SOCIEDAD": re.compile(
            r"CONFORMACI[OÓ]N\s+DE\s+LA\s+SOCIEDAD", re.IGNORECASE
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
