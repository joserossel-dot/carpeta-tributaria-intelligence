import re

from src.models.contributor import Contributor
from src.models.extract_result import ExtractResult
from src.models.section_result import SectionResult


class ContributorParser:
    """Extrae datos del contribuyente desde la sección IDENTIFICACION DEL CONTRIBUYENTE.

    Usa expresiones regulares para localizar cada campo.
    Si un campo no existe retorna None. Nunca lanza excepción por campos faltantes.
    """

    _RE_RUT = re.compile(
        r"RUT\s+del\s+[Ee]misor:\s*([\d.]+)\s*[-−]\s*([\dkK])"
    )
    _RE_RAZON_SOCIAL = re.compile(
        r"Nombre\s+del\s+[Ee]misor:\s*(.+)"
    )
    _RE_FECHA_GENERACION = re.compile(
        r"Fecha\s+de\s+generaci[oó]n\s+de\s+la\s+[Cc]arpeta:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})"
    )
    _RE_FECHA_INICIO = re.compile(
        r"Fecha\s+de\s+Inicio\s+de\s+Actividades:\s*(.+)"
    )
    _RE_DOMICILIO = re.compile(
        r"Domicilio:\s*(.+?)(?=\n\s*(?:Sucursales|Informaci[oó]n|Propiedades|Representante|-{3,}|$))",
        re.DOTALL,
    )
    _RE_TIPO_CONTRIBUYENTE = re.compile(
        r"Categor[ií]a\s+[Tt]ributaria:\s*(.+)"
    )
    _RE_REGIMEN = re.compile(
        r"R[eé]gimen\s+[Tt]ributario:\s*(.+)"
    )

    def parse(self, extract_result: ExtractResult, section_result: SectionResult) -> Contributor:
        """Analiza el texto extraído y retorna un Contributor con los datos encontrados.

        Args:
            extract_result: Texto extraído del PDF.
            section_result: Secciones detectadas en el PDF.

        Returns:
            Contributor con los campos que pudieron ser extraídos.
        """
        pages_text = self._get_pages_text(extract_result, section_result)

        if not pages_text:
            return Contributor()

        text = "\n".join(pages_text)

        rut = self._extract_rut(text)
        razon_social = self._extract_razon_social(text)
        fecha_generacion = self._extract_fecha_generacion(text)
        fecha_inicio = self._extract_fecha_inicio(text)
        domicilio_raw = self._extract_domicilio_raw(text)
        domicilio = self._normalize_domicilio(domicilio_raw)
        comuna = self._extract_comuna(domicilio_raw)
        region = None
        tipo = self._extract_tipo_contribuyente(text)
        regimen = self._extract_regimen(text)

        return Contributor(
            rut=rut,
            razon_social=razon_social,
            fecha_generacion=fecha_generacion,
            fecha_inicio_actividades=fecha_inicio,
            domicilio=domicilio,
            comuna=comuna,
            region=region,
            tipo_contribuyente=tipo,
            regimen_tributario=regimen,
        )

    def _get_pages_text(
        self, extract_result: ExtractResult, section_result: SectionResult
    ) -> list[str]:
        """Retorna el texto de las páginas donde se detectó la sección."""
        section_name = "IDENTIFICACION DEL CONTRIBUYENTE"
        pages = section_result.secciones.get(section_name, [])

        if pages:
            return [
                extract_result.pages[p - 1].text
                for p in pages
                if p - 1 < len(extract_result.pages)
            ]

        if extract_result.pages:
            return [extract_result.pages[0].text]

        return []

    def _extract_rut(self, text: str) -> str | None:
        m = self._RE_RUT.search(text)
        if not m:
            return None
        num, dv = m.group(1), m.group(2)
        return f"{num}-{dv.upper()}"

    def _extract_razon_social(self, text: str) -> str | None:
        m = self._RE_RAZON_SOCIAL.search(text)
        return m.group(1).strip() if m else None

    def _extract_fecha_generacion(self, text: str) -> str | None:
        m = self._RE_FECHA_GENERACION.search(text)
        return m.group(1).strip() if m else None

    def _extract_fecha_inicio(self, text: str) -> str | None:
        m = self._RE_FECHA_INICIO.search(text)
        return m.group(1).strip() if m else None

    def _extract_domicilio_raw(self, text: str) -> str | None:
        m = self._RE_DOMICILIO.search(text)
        return m.group(1).strip() if m else None

    def _normalize_domicilio(self, raw: str | None) -> str | None:
        if not raw:
            return None
        return re.sub(r"\s+", " ", raw)

    def _extract_comuna(self, domicilio_raw: str | None) -> str | None:
        if not domicilio_raw:
            return None
        first_line = domicilio_raw.split("\n")[0].strip()
        if "," not in first_line:
            return None
        after_comma = first_line.rsplit(",", 1)[1].strip()
        words = after_comma.split()
        return words[-1] if words else None

    def _extract_tipo_contribuyente(self, text: str) -> str | None:
        m = self._RE_TIPO_CONTRIBUYENTE.search(text)
        return m.group(1).strip() if m else None

    def _extract_regimen(self, text: str) -> str | None:
        m = self._RE_REGIMEN.search(text)
        return m.group(1).strip() if m else None
