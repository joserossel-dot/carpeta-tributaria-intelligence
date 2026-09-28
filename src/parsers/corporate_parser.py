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
    _RE_FECHA = re.compile(r"(\d{2}[/\-−]\d{2}[/\-−]\d{4})")
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

    _RE_FORMA_ACTUACION = re.compile(
        r"(en\s+conjunto|cualquiera|indistinta(?:mente)?|individual(?:mente)?|de\s+acuerdo\s+a\s+estatutos)",
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
        representantes, forma_act_global = self._extract_representantes_from_tables(extract_result)
        if not representantes:
            representantes = self._extract_personas(representantes_text, Representante, participacion=False)
            for r in representantes:
                if getattr(r, "forma_actuacion", None) and not forma_act_global:
                    forma_act_global = r.forma_actuacion

        return CorporateInfo(
            tipo_sociedad=tipo_sociedad,
            fecha_constitucion=fecha_constitucion,
            capital=capital,
            socios=socios,
            representantes=representantes,
            forma_actuacion_representantes=forma_act_global,
        )

    def _extract_representantes_from_tables(
        self, extract_result: ExtractResult
    ) -> tuple[list[Representante], str | None]:
        representantes: list[Representante] = []
        forma_global: str | None = None
        seen_ruts: set[str] = set()

        for page in getattr(extract_result, "pages", []):
            tables = getattr(page, "tables", []) or []
            for table in tables:
                in_rep_block = False
                for row in table:
                    row_str = " ".join(str(c or "") for c in row)
                    if not in_rep_block:
                        if re.search(r"REPRESENTANTE(?:\(?S\)?)?\s+LEGAL(?:\(?ES\)?)?", row_str, re.IGNORECASE):
                            in_rep_block = True
                    else:
                        if re.search(
                            r"CONFORMACI[OÓ]N(?:\s+DE\s+LA\s+SOCIEDAD)?|PARTICIPACI[OÓ]N|DECLARACI[OÓ]N|ACTIVIDAD|FORMULARIO|^\s*\(1\)|%\s+de\s+participaci[oó]n",
                            row_str,
                            re.IGNORECASE,
                        ):
                            in_rep_block = False
                            break

                    if in_rep_block:
                        rut_match = None
                        rut_idx = -1
                        for idx, cell in enumerate(row):
                            if cell and self._RE_RUT.search(str(cell)):
                                rut_match = self._RE_RUT.search(str(cell)).group(1)
                                rut_idx = idx
                                break

                        if rut_match and rut_idx > 0:
                            name_cands = [
                                row[i] for i in range(rut_idx)
                                if row[i] and str(row[i]).strip()
                                and not re.search(r"REPRESENTANTE(?:\(?S\)?)?\s+LEGAL(?:\(?ES\)?)?", str(row[i]), re.IGNORECASE)
                                and not re.search(r"Nombre\s+o\s+Raz", str(row[i]), re.IGNORECASE)
                            ]
                            if name_cands:
                                raw_name = str(name_cands[-1]).replace("\n", " ").replace("\r", " ").strip()
                                nombre = re.sub(r"\s+", " ", raw_name).strip(" .-")

                                fecha_inc = None
                                forma_act = None
                                vigente = True

                                for cell in row[rut_idx + 1:]:
                                    c_str = str(cell or "").strip()
                                    if not c_str:
                                        continue
                                    m_f = self._RE_FECHA.search(c_str)
                                    if m_f and not fecha_inc:
                                        fecha_inc = m_f.group(1)
                                    m_forma = self._RE_FORMA_ACTUACION.search(c_str)
                                    if m_forma and not forma_act:
                                        raw_forma = m_forma.group(1).strip()
                                        if "conjunto" in raw_forma.lower():
                                            forma_act = "En conjunto"
                                        elif "cualquiera" in raw_forma.lower():
                                            forma_act = "Cualquiera"
                                        else:
                                            forma_act = raw_forma.capitalize()
                                        if not forma_global:
                                            forma_global = forma_act

                                    if re.search(r"t[eé]rmino|cese|inactivo|revocado", c_str, re.IGNORECASE):
                                        vigente = False

                                if nombre and len(nombre) >= 4 and rut_match not in seen_ruts:
                                    seen_ruts.add(rut_match)
                                    if vigente:
                                        representantes.append(
                                            Representante(
                                                rut=rut_match,
                                                nombre=nombre,
                                                cargo=None,
                                                fecha_incorporacion=fecha_inc,
                                                forma_actuacion=forma_act,
                                                vigente=vigente,
                                            )
                                        )

        return representantes, forma_global

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
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        i = 0
        while i < len(lines):
            line = lines[i]
            if len(line) < 8:
                i += 1
                continue

            rut_match = self._RE_RUT.search(line)
            if not rut_match:
                i += 1
                continue

            rut = rut_match.group(1)
            nombre = line[: rut_match.start()].strip(" .-")
            nombre = re.sub(r"\s+", " ", nombre)

            # Si la línea siguiente es una continuación de apellido/nombre (sin RUT, sin dígitos ni stop headings)
            if i + 1 < len(lines):
                next_l = lines[i + 1]
                if (
                    not self._RE_RUT.search(next_l)
                    and not self._RE_FECHA.search(next_l)
                    and not self._STOP_HEADINGS.search(next_l)
                    and not any(k in next_l.upper() for k in ["DECLARACI", "ACTIVIDAD", "FORMULARIO", "(1)"])
                    and len(next_l.split()) <= 3
                    and re.match(r"^[A-Za-zÁ-Úá-ú\s]+$", next_l)
                ):
                    nombre = f"{nombre} {next_l}".strip()
                    nombre = re.sub(r"\s+", " ", nombre)

            # Filtra encabezados de tabla ("Nombre o Razon Social RUT...")
            # que no son una fila de datos real.
            if not nombre or len(nombre) < 4 or "RAZ" in nombre.upper():
                i += 1
                continue

            resto = line[rut_match.end():].strip()

            if rut in seen:
                i += 1
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
                forma_match = self._RE_FORMA_ACTUACION.search(resto)
                if forma_match:
                    raw_f = forma_match.group(1).strip()
                    forma = "En conjunto" if "conjunto" in raw_f.lower() else ("Cualquiera" if "cualquiera" in raw_f.lower() else raw_f.capitalize())
                else:
                    forma = None
                personas.append(model_cls(rut=rut, nombre=nombre, cargo=None, forma_actuacion=forma))

            i += 1

        return personas
