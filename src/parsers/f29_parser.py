import re
from typing import Pattern

from src.models.extract_result import ExtractResult
from src.models.f29 import F29, F29Detail
from src.models.section_result import SectionResult


class F29Parser:
    """Parser del Formulario 29 (Declaración Mensual de IVA).

    Localiza las páginas F29 mediante SectionDetector,
    detecta cada formulario individual y extrae todos los códigos tributarios.
    """

    _RE_FOLIO = re.compile(
        r"FOLIO\s+(?:\S+\s+)?(\d+)", re.IGNORECASE
    )
    _RE_PERIODO_NUEVO = re.compile(
        r"PERIODO\s+(?:\[15\]\s*)?(\d{4})(\d{2})"
    )
    _RE_PERIODO_VIEJO = re.compile(
        r"PERIODO\s+15\s+(\d{1,2})\s*/\s*(\d{4})"
    )
    _RE_FECHA_PRESENTACION = re.compile(
        r"(\d{2}/\d{2}/\d{4})\s*$"
    )
    _RE_ENCABEZADO_F29_START = re.compile(
        r"DECLARACI[ÓO]N\s+MENSUAL\s+Y\s+PAGO", re.IGNORECASE
    )
    _RE_SIN_DECLARACION = re.compile(
        r"No\s+se\s+registra\s+declaraci[óo]n", re.IGNORECASE
    )
    _RE_TABLA_HEADER = re.compile(
        r"C[óo]digo\s+Glosa\s+Valor.*", re.IGNORECASE
    )
    _RE_CODE_TUPLE: Pattern[str] = re.compile(
        r"(\d{3})\s+(.+?)\s+(-?[\d.,]+)(?=\s+\d{3}|$)"
    )
    _RE_PAGINA_MARCA = re.compile(
        r"(?:P[áa]g\.?\s*|^\s*)\d+\s*/\s*\d+\s*$", re.MULTILINE
    )
    _RE_FIN_SECCION_TOTALES = re.compile(
        r"TOTAL\s+A\s+PAGAR\s+DENTRO\s+DEL\s+PLAZO\s+LEGAL",
        re.IGNORECASE,
    )
    _RE_LINEA_CONTINUACION = re.compile(r"^\d{3}")
    _RE_FECHA_EN_LINEA = re.compile(r"(\d{2}/\d{2}/\d{4})")
    _HEADERS_IGNORAR = [
        r"Apellido\s+Paterno",
        r"Calle",
        r"Tel[eé]fono",
        r"C[óo]digo\s+Glosa\s+Valor",
        r"FORMULARIO\s+29",
        r"RUT\s+\d+",
    ]

    def parse(self, extract_result: ExtractResult, section_result: SectionResult) -> list[F29]:
        pages = section_result.secciones.get("FORMULARIO 29", [])
        if not pages:
            return []

        forms: list[F29] = []

        for page_num in pages:
            if page_num - 1 >= len(extract_result.pages):
                continue
            text = extract_result.pages[page_num - 1].text
            form = self._parse_page(text)
            if form is not None:
                forms.append(form)

        forms.sort(key=lambda f: f.periodo or "", reverse=True)
        return forms

    def _parse_page(self, text: str) -> F29 | None:
        if self._RE_SIN_DECLARACION.search(text):
            return None
        if not self._RE_ENCABEZADO_F29_START.search(text):
            return None

        folio = self._extract_folio(text)
        periodo = self._extract_periodo(text)
        detalle_lines = self._extract_detalle_lines(text)
        detalles = self._parse_detalles(detalle_lines)
        fecha_presentacion = self._extract_fecha_presentacion(text)

        if not folio and not periodo:
            return None

        return F29(
            periodo=periodo or "",
            folio=folio or "",
            fecha_presentacion=fecha_presentacion,
            detalles=detalles,
        )

    def _extract_folio(self, text: str) -> str | None:
        m = self._RE_FOLIO.search(text)
        return m.group(1) if m else None

    def _extract_periodo(self, text: str) -> str | None:
        m = self._RE_PERIODO_NUEVO.search(text)
        if m:
            year, month = m.group(1), m.group(2)
            return f"{year}-{month}"
        m = self._RE_PERIODO_VIEJO.search(text)
        if m:
            month, year = m.group(1), m.group(2)
            return f"{year}-{int(month):02d}"
        return None

    def _extract_fecha_presentacion(self, text: str) -> str | None:
        idx = text.find("Fecha de Presentaci")
        if idx == -1:
            idx = text.find("Fecha de presentaci")
        if idx == -1:
            return None
        segment = text[idx:]
        fechas = self._RE_FECHA_EN_LINEA.findall(segment)
        return fechas[-1] if fechas else None

    def _extract_detalle_lines(self, text: str) -> list[str]:
        idx = self._RE_TABLA_HEADER.search(text)
        if not idx:
            return []
        start = idx.end()
        rest = text[start:]

        fin = self._RE_FIN_SECCION_TOTALES.search(rest)
        if fin:
            rest = rest[: fin.start()]

        lines = rest.split("\n")
        result = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if self._es_header_ignorable(line):
                continue
            result.append(line)
        return result

    @staticmethod
    def _es_header_ignorable(line: str) -> bool:
        return any(re.search(p, line, re.IGNORECASE) for p in F29Parser._HEADERS_IGNORAR)

    def _parse_detalles(self, lines: list[str]) -> list[F29Detail]:
        joined = self._join_continuation_lines(lines)
        detalles: list[F29Detail] = []
        for line in joined:
            matches = self._RE_CODE_TUPLE.findall(line)
            for codigo, glosa, valor in matches:
                valor_clean = valor.replace(".", "").replace(",", ".") if valor else valor
                detalles.append(F29Detail(
                    codigo=codigo,
                    glosa=glosa.strip(),
                    valor=valor_clean,
                ))
        return detalles

    @staticmethod
    def _join_continuation_lines(lines: list[str]) -> list[str]:
        result: list[str] = []
        for line in lines:
            if re.match(r"^\d{3}", line):
                result.append(line)
            elif result:
                result[-1] += " " + line
            else:
                result.append(line)
        return result
