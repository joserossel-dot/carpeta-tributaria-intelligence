import re

from src.models.contributor import Contributor


class ContributorParser:
    """Extrae los datos de identificacion del contribuyente.

    El SII imprime estos datos como lineas "Etiqueta: valor" al inicio
    de la carpeta (normalmente pagina 1), NO dentro de una seccion con
    encabezado propio -- por eso este parser no depende de SectionDetector
    y trabaja directo sobre el texto completo de la primera pagina.
    """

    # re.IGNORECASE en todo: el SII no es consistente entre formatos de
    # carpeta -- a veces "Nombre del emisor", a veces "Nombre del Emisor".
    _RE_RAZON_SOCIAL = re.compile(r"Nombre del emisor:\s*(.+)", re.IGNORECASE)
    _RE_RUT = re.compile(r"RUT del emisor:\s*([\d.]+\s*[-−]\s*[\dkK])", re.IGNORECASE)
    _RE_FECHA_GENERACION = re.compile(
        r"Fecha de generaci[oó]n de la carpeta:\s*([\d/]+(?:\s+[\d:]+)?)", re.IGNORECASE
    )
    _RE_FECHA_INICIO = re.compile(
        r"Fecha de Inicio de Actividades:\s*(.+)", re.IGNORECASE
    )
    # "Categoria tributaria" (Primera/Segunda categoria) y "Regimen
    # Tributario" (ProPyme, 14A, etc.) son conceptos DISTINTOS en el SII.
    # El formato viejo de carpeta solo trae categoria; el nuevo trae ambos.
    _RE_CATEGORIA = re.compile(r"Categor[ií]a tributaria:\s*(.+)", re.IGNORECASE)
    _RE_REGIMEN = re.compile(r"R[eé]gimen [Tt]ributario:\s*(.+)", re.IGNORECASE)
    _RE_DOMICILIO = re.compile(r"Domicilio:\s*(.+)", re.IGNORECASE)
    # El domicilio del emisor puede seguir en las lineas siguientes hasta
    # que empieza el bloque de sucursales u otra seccion -- a diferencia de
    # las demas etiquetas (una sola linea), este campo puede ser multilinea.
    _RE_DOMICILIO_STOP = re.compile(
        r"^\s*(Sucursales:|Informaci[oó]n proporcionada|Representante|"
        r"Conformaci[oó]n de la sociedad|Actividad(?:es)? [Ee]con[oó]mica)",
        re.IGNORECASE,
    )

    def parse(self, extract_result, section_result) -> Contributor:
        text = self._get_text(extract_result, section_result)
        if not text:
            return Contributor()

        primera_linea_domicilio, domicilio = self._extract_domicilio(text)

        return Contributor(
            razon_social=self._clean(self._match(self._RE_RAZON_SOCIAL, text)),
            rut=self._clean_rut(self._match(self._RE_RUT, text)),
            fecha_generacion=self._clean(self._match(self._RE_FECHA_GENERACION, text)),
            fecha_inicio_actividades=self._clean(self._match(self._RE_FECHA_INICIO, text)),
            tipo_contribuyente=self._clean(self._match(self._RE_CATEGORIA, text)),
            regimen_tributario=self._clean(self._match(self._RE_REGIMEN, text)),
            domicilio=domicilio,
            comuna=self._extract_comuna(primera_linea_domicilio),
        )

    def _extract_domicilio(self, text: str) -> tuple[str | None, str | None]:
        """Devuelve (primera_linea, domicilio_completo).

        El domicilio del SII puede extenderse por varias lineas (direccion
        principal + informacion adicional) antes del bloque "Sucursales:"
        u otra seccion. La comuna se calcula solo sobre la primera linea
        (la direccion principal), no sobre las lineas de sucursales.
        """
        m = self._RE_DOMICILIO.search(text)
        if not m:
            return None, None

        start = m.end() - len(m.group(1))
        resto = text[start:]
        lineas = resto.split("\n")

        primera_linea = lineas[0].strip()
        bloque = [primera_linea] if primera_linea else []
        for linea in lineas[1:]:
            if self._RE_DOMICILIO_STOP.match(linea):
                break
            linea = linea.strip()
            if linea:
                bloque.append(linea)

        domicilio = " ".join(bloque).strip() or None
        return (primera_linea or None), domicilio

    def _get_text(self, extract_result, section_result) -> str:
        if hasattr(extract_result, "pages") and extract_result.pages:
            # Los datos del emisor siempre estan en la primera pagina.
            return extract_result.pages[0].text
        if hasattr(section_result, "text") and section_result.text:
            return section_result.text
        if isinstance(extract_result, str):
            return extract_result
        return ""

    @staticmethod
    def _match(pattern: re.Pattern, text: str) -> str | None:
        m = pattern.search(text)
        return m.group(1) if m else None

    @staticmethod
    def _clean(value: str | None) -> str | None:
        if value is None:
            return None
        # Corta en el primer salto de linea: estas etiquetas son de una sola
        # linea salvo Domicilio, que puede seguir en lineas siguientes -- se
        # deja solo la primera linea para evitar arrastrar la seccion siguiente.
        return value.split("\n")[0].strip() or None

    @staticmethod
    def _clean_rut(value: str | None) -> str | None:
        if value is None:
            return None
        rut = re.sub(r"\s+", "", value.split("\n")[0])
        return rut.replace("−", "-").strip() or None

    @staticmethod
    def _extract_comuna(domicilio: str | None) -> str | None:
        """Heuristica: el ultimo tramo separado por coma de la direccion
        suele incluir la comuna en el formato de domicilio del SII.
        No es exacto (el SII no separa comuna en un campo propio en el
        texto), pero es mejor que dejarlo vacio.
        """
        if not domicilio:
            return None
        partes = [p.strip() for p in domicilio.split(",") if p.strip()]
        return partes[-1] if partes else None
