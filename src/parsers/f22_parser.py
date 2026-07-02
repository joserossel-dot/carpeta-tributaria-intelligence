import re

from src.models.annual_tax_return import AnnualTaxReturn
from src.models.extract_result import ExtractResult
from src.models.section_result import SectionResult


class F22Parser:
    CODE_MAP: dict[str, str] = {
        "36": "ppm",
        "82": "creditos",
        "305": "impuesto_determinado",
        "645": "capital_propio_tributario",
        "646": "perdidas",
        "844": "capital_propio_tributario",
        "1109": "base_imponible",
        "1657": "ingresos",
        "1690": "resultado_tributario",
        "1694": "renta_liquida_imponible",
    }

    # Priority: when multiple codes map to the same field, higher priority wins
    CODE_PRIORITY: dict[str, int] = {
        "36": 100,
        "82": 100,
        "305": 100,
        "645": 10,   # CPT positivo final (lower priority)
        "646": 100,
        "844": 20,   # Capital propio tributario (higher priority than 645)
        "1109": 100,
        "1657": 100,
        "1690": 100,
        "1694": 100,
    }

    def parse(self, extract_result: ExtractResult, section_result: SectionResult) -> list[AnnualTaxReturn]:
        f22_pages = section_result.secciones.get("FORMULARIO 22", [])
        if not f22_pages:
            return []

        pages_text = self._get_range_text(extract_result, f22_pages)
        if not pages_text.strip():
            return []

        forms = self._split_forms(pages_text)
        results: list[AnnualTaxReturn] = []

        for anio, text in forms:
            result = self._parse_form(anio, text)
            results.append(result)

        results.sort(key=lambda r: r.anio_tributario or "", reverse=True)
        return results

    @staticmethod
    def _get_range_text(extract_result: ExtractResult, f22_pages: list[int]) -> str:
        sorted_pages = sorted(f22_pages)
        first = sorted_pages[0]
        last = min(sorted_pages[-1] + 2, len(extract_result.pages))
        parts: list[str] = []
        for pn in range(first, last + 1):
            if pn - 1 < len(extract_result.pages):
                parts.append(extract_result.pages[pn - 1].text)
        return "\n".join(parts)

    @staticmethod
    def _split_forms(text: str) -> list[tuple[str, str]]:
        pattern = re.compile(
            r"REPUBLICA\s+DE\s+CHILE\s+A[ÑN]O\s+TRIBUTARIO\s+(\d{4})",
            re.IGNORECASE,
        )
        splits = list(pattern.finditer(text))
        if not splits:
            return []

        forms: list[tuple[str, str]] = []
        for i, m in enumerate(splits):
            anio = m.group(1)
            start = m.start()
            end = splits[i + 1].start() if i + 1 < len(splits) else len(text)
            form_text = text[start:end]
            forms.append((anio, form_text))
        return forms

    def _parse_form(self, anio: str, text: str) -> AnnualTaxReturn:
        text = self._normalize(text)
        # Remove the calculation/result section ("Folio N°" onwards) to avoid
        # spurious matches of codes like 305 in "código 305 % 39".
        folio_idx = text.find("Folio N°")
        if folio_idx != -1:
            text = text[:folio_idx]
        pairs = self._extract_code_value_pairs(text)
        return self._build_return(anio, pairs)

    @staticmethod
    def _normalize(text: str) -> str:
        """Join continuation lines and collapse whitespace."""
        lines = text.split("\n")
        result: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if re.match(r"\d{2,4}\s", stripped):
                result.append(stripped)
            elif result:
                result[-1] += " " + stripped
        return "\n".join(result)

    @staticmethod
    def _extract_code_value_pairs(text: str) -> list[tuple[str, str, str]]:
        pairs: list[tuple[str, str, str]] = []
        RE_VAL = re.compile(r"-?\d[\d.]*")
        RE_CODE = re.compile(r"(?<!\d)(\d{2,4})(?!\d)")

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue

            code_matches = list(RE_CODE.finditer(line))
            val_matches = list(RE_VAL.finditer(line))
            if not code_matches or not val_matches:
                continue

            for code_m in code_matches:
                code = code_m.group(1)
                code_end = code_m.end()
                # Pick the LAST value on the line — F22 always puts the value
                # at the end, with description/glosa in between.
                # This avoids picking numbers embedded in glosas (e.g.,
                # "Ley N° 19.518" → picks 7.000.000, not 19).
                last_val = val_matches[-1]
                label = line[code_end:last_val.start()].strip()
                value = last_val.group(0)
                pairs.append((code, label, value))

        return pairs

    def _build_return(self, anio: str, pairs: list[tuple[str, str, str]]) -> AnnualTaxReturn:
        # Track which code set each field (for priority overwrite)
        field_source: dict[str, str] = {}
        values: dict[str, int | None] = {
            "ingresos": None,
            "renta_liquida_imponible": None,
            "capital_propio_tributario": None,
            "impuesto_determinado": None,
            "ppm": None,
            "creditos": None,
            "perdidas": None,
            "base_imponible": None,
            "resultado_tributario": None,
        }
        observaciones: list[str] = []

        for codigo_str, _label, valor_str in pairs:
            campo = self.CODE_MAP.get(codigo_str)
            if campo is None:
                continue
            valor = self._parse_int(valor_str)
            if valor is None:
                continue
            if campo == "impuesto_determinado":
                values[campo] = valor
                field_source[campo] = codigo_str
            elif campo == "perdidas":
                if values[campo] is None or valor > (values[campo] or 0):
                    values[campo] = valor
                    field_source[campo] = codigo_str
            else:
                source = field_source.get(campo)
                if source is None or self.CODE_PRIORITY.get(codigo_str, 0) > self.CODE_PRIORITY.get(source, 0):
                    values[campo] = valor
                    field_source[campo] = codigo_str

        if values["capital_propio_tributario"] is None:
            observaciones.append("No se encontró Capital Propio Tributario")

        if values["ingresos"] is None:
            observaciones.append("No se encontraron Ingresos del Giro")

        return AnnualTaxReturn(
            anio_tributario=anio,
            ingresos=values["ingresos"],
            renta_liquida_imponible=values["renta_liquida_imponible"],
            capital_propio_tributario=values["capital_propio_tributario"],
            impuesto_determinado=values["impuesto_determinado"],
            ppm=values["ppm"],
            creditos=values["creditos"],
            perdidas=values["perdidas"],
            base_imponible=values["base_imponible"],
            resultado_tributario=values["resultado_tributario"],
            observaciones=observaciones,
        )

    @staticmethod
    def _parse_int(valor: str) -> int | None:
        cleaned = valor.replace(".", "").strip()
        if not cleaned or cleaned in ("-", ""):
            return None
        try:
            return int(cleaned)
        except ValueError:
            return None
