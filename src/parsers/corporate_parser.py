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
    _RE_SOCIO_LINE = re.compile(
        r"(\d{1,2}\.\d{3}\.\d{3}[-−]\d)\s+(.+?)"  # RUT + nombre
    )
    _RE_SOCIO_PCT = re.compile(
        r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*%"
    )
    _RE_REPR_LINE = re.compile(
        r"(\d{1,2}\.\d{3}\.\d{3}[-−]\d)\s+(.+?)(?:\s+(?:Representante\s+Legal|Administrador|Gerente|Director|Presidente))?$",
        re.IGNORECASE,
    )

    def parse(
        self, extract_result: ExtractResult, section_result: SectionResult
    ) -> CorporateInfo:
        conformacion_pages = section_result.secciones.get(
            "CONFORMACION DE LA SOCIEDAD", []
        )
        representantes_pages = section_result.secciones.get(
            "REPRESENTANTES LEGALES", []
        )

        conformacion_text = self._get_text(extract_result, conformacion_pages)
        representantes_text = self._get_text(extract_result, representantes_pages)

        tipo_sociedad = self._extract_tipo_sociedad(conformacion_text)
        capital = self._extract_capital(conformacion_text)
        fecha_constitucion = self._extract_fecha_constitucion(
            conformacion_text or representantes_text
        )
        socios = self._extract_socios(conformacion_text)
        representantes = self._extract_representantes(representantes_text)

        return CorporateInfo(
            tipo_sociedad=tipo_sociedad,
            fecha_constitucion=fecha_constitucion,
            capital=capital,
            socios=socios,
            representantes=representantes,
        )

    def _get_text(
        self, extract_result: ExtractResult, pages: list[int]
    ) -> str:
        texts: list[str] = []
        for p in pages:
            if p - 1 < len(extract_result.pages):
                texts.append(extract_result.pages[p - 1].text)
        return "\n".join(texts)

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

    def _extract_socios(self, text: str) -> list[Socio]:
        if not text:
            return []
        socios: list[Socio] = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            rut_match = self._RE_SOCIO_LINE.search(line)
            if not rut_match:
                continue
            rut = rut_match.group(1).strip()
            rest = line[rut_match.end() :].strip()
            pct_match = self._RE_SOCIO_PCT.search(rest)
            participacion = pct_match.group(1) if pct_match else None
            nombre = rest[: pct_match.start()].strip() if pct_match else rest
            nombre = re.sub(r"\s+", " ", nombre).strip()
            socios.append(Socio(rut=rut, nombre=nombre, participacion=participacion))
        return socios

    def _extract_representantes(self, text: str) -> list[Representante]:
        if not text:
            return []
        representantes: list[Representante] = []
        cargo_map = {
            "representante legal": "Representante Legal",
            "administrador": "Administrador",
            "gerente": "Gerente",
            "director": "Director",
            "presidente": "Presidente",
        }
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = re.split(r"\s{2,}", line)
            if len(parts) < 2:
                continue
            rut_part = parts[0].strip()
            if not re.match(r"\d{1,2}\.\d{3}\.\d{3}[-−]\d", rut_part):
                continue
            nombre_raw = parts[1].strip()
            cargo = None
            for key, val in cargo_map.items():
                if key in nombre_raw.lower():
                    cargo = val
                    nombre_raw = re.sub(
                        r"\s+" + re.escape(key) + r"\s*$",
                        "",
                        nombre_raw,
                        flags=re.IGNORECASE,
                    ).strip()
                    break
            nombre = re.sub(r"\s+", " ", nombre_raw).strip()
            representantes.append(
                Representante(rut=rut_part, nombre=nombre, cargo=cargo)
            )
        return representantes
