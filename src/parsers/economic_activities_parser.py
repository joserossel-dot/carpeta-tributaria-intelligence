import re

from src.models.activity import Activity
from src.models.extract_result import ExtractResult
from src.models.section_result import SectionResult

_RE_CODE = re.compile(r"^\d{6}")
_RE_OLD_LINE = re.compile(r"^(\d{6})\s+(.+)$")
_RE_NEW_LINE = re.compile(
    r"^(\d{6})\s+(.+?)\s+(Primera\s+Categor[aí]a|Segunda\s+Categor[aí]a)\s+(\d{2}/\d{2}/\d{4})",
    re.IGNORECASE,
)
_RE_TABLE_HEADER = re.compile(
    r"C[óo]digo\s+Actividad\s+Categor[aí]a\s+Tributaria\s+A\s+partir\s+de",
    re.IGNORECASE,
)
_RE_BOUNDARY = re.compile(
    r"\n\s*Categor[aí]a\s+[Tt]ributaria:", re.IGNORECASE
)


class EconomicActivitiesParser:
    def parse(self, extract_result: ExtractResult, section_result: SectionResult) -> list[Activity]:
        pages = section_result.secciones.get("ACTIVIDADES ECONOMICAS", [])
        if not pages:
            return []

        text_parts: list[str] = []
        for p in pages:
            if p - 1 < len(extract_result.pages):
                text_parts.append(extract_result.pages[p - 1].text)

        text = "\n".join(text_parts)

        start = text.find("Actividades Econ")
        if start == -1:
            start = text.find("ACTIVIDADES ECON")
        if start == -1:
            return []

        section = text[start:]
        boundary = _RE_BOUNDARY.search(section)
        if boundary:
            section = section[: boundary.start()]

        is_new = bool(_RE_TABLE_HEADER.search(section))

        if is_new:
            return self._parse_new_format(section)
        return self._parse_old_format(section)

    def _parse_old_format(self, section: str) -> list[Activity]:
        lines = section.split("\n")
        raw_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if _RE_CODE.match(stripped):
                raw_lines.append(stripped)
            elif raw_lines:
                raw_lines[-1] += " " + stripped

        activities: list[Activity] = []
        for i, raw in enumerate(raw_lines):
            m = _RE_OLD_LINE.match(raw)
            if m:
                activities.append(
                    Activity(
                        codigo=m.group(1),
                        descripcion=m.group(2).strip(),
                        principal=i == 0,
                    )
                )
        return activities

    def _parse_new_format(self, section: str) -> list[Activity]:
        header = _RE_TABLE_HEADER.search(section)
        if not header:
            return []

        body = section[header.end() :]
        lines = body.split("\n")
        raw_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if _RE_CODE.match(stripped):
                raw_lines.append(stripped)
            elif raw_lines:
                raw_lines[-1] += " " + stripped

        activities: list[Activity] = []
        for i, raw in enumerate(raw_lines):
            m = _RE_NEW_LINE.match(raw)
            if m:
                desc = m.group(2).strip()
                tail = raw[m.end() :].strip()
                if tail:
                    desc += " " + tail
                activities.append(
                    Activity(
                        codigo=m.group(1),
                        descripcion=desc,
                        principal=i == 0,
                        categoria=m.group(3).strip(),
                        fecha_inicio=m.group(4).strip(),
                    )
                )
        return activities
