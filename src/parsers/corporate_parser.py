import re

from src.models.corporate import CorporateInfo, Representante, Socio
from src.models.extract_result import ExtractResult
from src.models.section_result import SectionResult


class CorporateParser:
    _RE_TIPO_SOCIEDAD = re.compile(
        r"Sociedad\s+(?:del\s+)?[Tt]ipo:\s*(.+)", re.IGNORECASE
    )
    _RE_CAPITAL = re.compile(
        r"Capital\s*(?:[Ss]ocial|[Cc]onstitutivo)?:\s*\$?\s*([\d.]+)",
        re.IGNORECASE,
    )
    _RE_FECHA_CONSTITUCION = re.compile(
        r"Fecha\s+de\s+[Cc]onstituci[oó]n:\s*(\d{2}[/\-]\d{2}[/\-]\d{4})",
        re.IGNORECASE,
    )
    # RUT con o sin puntos de miles: "5603821-3" o "5.603.821-3".
    _RE_RUT = re.compile(r"(\d{1,2}(?:\.?\d{3}){2}[-−][\dkK])")
    _RE_FECHA = re.compile(r"(\d{2}[-−]\d{2}[-−]\d{4})")
    _RE_PCT = re.compile(r"(\d{1,3}(?:[.,]\d{1,2})?)\s*%")

    # Encabezados que marcan donde termina un bloque de nombres (para no
    # arrastrar la seccion siguiente al extraer una tabla).
    _STOP_HEADINGS = re.compile(
        r"CONFORMACI[OÓ]N\s+DE\s+LA\s+SOCIEDAD"
        r"|REPRESENTANTE(?:\(?S\)?)?\s+LEGAL(?:\(?ES\)?)?"
        r"|ACTIVIDAD(?:ES)?\s+ECON[OÓ]MICA(?:S)?"
        r"|FORMULARIO\s+2[29]"
        r"|DECLARACI[OÓ]N(?:ES)?\s+JURADA(?:S)?",
        re.IGNORECASE,
    )

    def parse(
        self, extract_result: ExtractResult, section_result: SectionResult
    ) -> CorporateInfo:
        full_text = "\n".join(p.text for p in extract_result.pages)

        conformacion_text = self._slice_after(full_text, [
            r"CONFORMACI[OÓ]N\s+DE\s+LA\s+SOCIEDAD",
        ])
        representantes_text = self._slice_after(full_text, [
            r"REPRESENTANTE(?:\(?S\)?)?\s+LEGAL(?:\(?ES\)?)?",
        ])

        tipo_sociedad = self._extract_tipo_sociedad(conformacion_text)
        capital = self._extract_capital(conformacion_text)
        fecha_constitucion = self._extract_fecha_constitucion(
            conformacion_text or representantes_text
        )
        socios = self._extract_personas(conformacion_text, Socio, participacion=True)
        representantes = self._extract_personas(representantes_text, Representante, participacion=False)

        return CorporateInfo(
            tipo_sociedad=tipo_sociedad,
            fecha_constitucion=fecha_constitucion,
            capital=capital,
            socios=socios,
            representantes=representantes,
        )

    def _slice_after(self, text: str, heading_patterns: list[str]) -> str:
        """Devuelve el texto desde el encabezado buscado hasta el proximo
        encabezado conocido (o 2000 caracteres si no encuentra ninguno)."""
        for hp in heading_patterns:
            m = re.search(hp, text, re.IGNORECASE)
            if not m:
                continue
            start = m.end()
            resto = text[start:start + 3000]
            stop = self._STOP_HEADINGS.search(resto)
            return resto[: stop.start()] if stop else resto
        return ""

    def _extract_tipo_sociedad(self, text: str) -> str | None:
        if not text:
            return None
        m = self._RE_TIPO_SOCIEDAD.search(text)
        return m.group(1).strip() if m else None

    def _extract_capital(self, text: str) -> str | None:
        if not text:
            return None
        m = self._RE_CAPITAL.search(text)
        return m.group(1).strip() if m else None

    def _extract_fecha_constitucion(self, text: str) -> str | None:
        if not text:
            return None
        m = self._RE_FECHA_CONSTITUCION.search(text)
        return m.group(1).strip() if m else None

    def _extract_personas(self, text: str, model_cls, participacion: bool):
        """Extrae filas 'NOMBRE RUT [FECHA|%]' -- el formato real del SII
        pone el nombre primero y el RUT despues, al reves de lo que
        asumia la version anterior de este parser."""
        if not text:
            return []

        personas = []
        seen = set()
        for line in text.split("\n"):
            line = line.strip()
            if not line or len(line) < 8:
                continue

            rut_match = self._RE_RUT.search(line)
            if not rut_match:
                continue

            rut = rut_match.group(1)
            nombre = line[: rut_match.start()].strip(" .-")
            nombre = re.sub(r"\s+", " ", nombre)

            # Filtra encabezados de tabla ("Nombre o Razon Social RUT...")
            # que no son una fila de datos real.
            if not nombre or len(nombre) < 4 or "RAZ" in nombre.upper():
                continue

            resto = line[rut_match.end():].strip()

            if rut in seen:
                continue
            seen.add(rut)

            if participacion:
                pct_match = self._RE_PCT.search(resto)
                personas.append(
                    model_cls(
                        rut=rut,
                        nombre=nombre,
                        participacion=f"{pct_match.group(1)}%" if pct_match else None,
                    )
                )
            else:
                personas.append(model_cls(rut=rut, nombre=nombre, cargo=None))

        return personas
