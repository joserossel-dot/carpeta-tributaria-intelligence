import re

from src.models.annual_tax_return import AnnualTaxReturn


class F22Parser:
    """Extrae las declaraciones del Formulario 22 (Renta Anual).

    Cada pagina de F22 en la Carpeta Tributaria corresponde normalmente a
    UN año tributario, pero un mismo año puede continuar en la pagina
    siguiente sin repetir el encabezado "AÑO TRIBUTARIO". Este parser:
      1. agrupa paginas consecutivas del F22 en "bloques" (una declaracion
         empieza donde aparece un encabezado de año nuevo, y se extiende a
         las paginas siguientes que no traigan su propio encabezado ni
         pertenezcan claramente a otra seccion),
      2. extrae los codigos de linea SII reales de cada bloque,
      3. devuelve una declaracion (AnnualTaxReturn) por año, con la mas
         reciente primero.

    Los codigos de linea usados aqui corresponden al Formulario 22 vigente
    del SII (ver tests/test_f22_parser.py, que documenta el mapeo real):
      1657 = Ingresos del giro
      1694 = Renta Liquida Imponible (o perdida)
      844  = Capital Propio Tributario
      36   = Pagos Provisionales Mensuales (PPM)
      82   = Creditos
      1109 = Base Imponible
      305  = Resultado de la liquidacion anual del Impuesto a la Renta
    """

    _CODIGO_MAPPING = {
        "1657": "ingresos",
        "1694": "renta_liquida_imponible",
        "844": "capital_propio_tributario",
        "36": "ppm",
        "82": "creditos",
        "1109": "base_imponible",
        "305": "impuesto_determinado",
    }

    _RE_ANIO = re.compile(r"A(?:ÑO|NO|NIO)\s+TRIBUTARIO\s*(\d{4})", re.IGNORECASE)
    _RE_SIN_DECLARACION = re.compile(r"No se registra declaraci[oó]n", re.IGNORECASE)

    # Encabezados de otras secciones: si aparecen en una pagina sin su
    # propio marcador de año, esa pagina NO se trata como continuacion del
    # F22 anterior (evita "tragarse" Bienes Raices, Vehiculos, etc.).
    _RE_OTRA_SECCION = re.compile(
        r"BIENES\s+RA[IÍ]CE(?:S)?"
        r"|VEH[IÍ]CULO(?:S)?"
        r"|DECLARACI[OÓ]N(?:ES)?\s+JURADA(?:S)?"
        r"|CONFORMACI[OÓ]N\s+DE\s+LA\s+SOCIEDAD"
        r"|REPRESENTANTE(?:\(?S\)?)?\s+LEGAL(?:\(?ES\)?)?"
        r"|ACTIVIDAD(?:ES)?\s+ECON[OÓ]MICA(?:S)?",
        re.IGNORECASE,
    )

    # Mensajes exactos (conjugacion distinta por campo, ver tests).
    _OBSERVACIONES_CAMPOS_FALTANTES = {
        "ingresos": "No se encontraron Ingresos del Giro",
        "renta_liquida_imponible": "No se encontró Renta Líquida Imponible",
        "capital_propio_tributario": "No se encontró Capital Propio Tributario",
    }

    def parse(self, extract_result, section_result) -> list[AnnualTaxReturn]:
        pages = getattr(extract_result, "pages", None) or []
        if not pages:
            return []

        paginas_listadas = set(section_result.secciones.get("FORMULARIO 22", []))
        bloques = self._agrupar_bloques(pages, paginas_listadas)

        declaraciones = []
        anios_vistos = set()
        for texto_bloque in bloques:
            anio = self._detectar_anio(texto_bloque)
            if not anio or anio in anios_vistos:
                continue
            if self._RE_SIN_DECLARACION.search(texto_bloque):
                continue
            anios_vistos.add(anio)
            declaraciones.append(self._extraer_datos(texto_bloque, anio))

        declaraciones.sort(key=lambda d: d.anio_tributario, reverse=True)
        return declaraciones

    def _agrupar_bloques(self, pages, paginas_listadas: set[int]) -> list[str]:
        bloques = []
        actual: list[str] = []
        activo = False

        for page in pages:
            texto = page.text or ""
            tiene_marcador = bool(self._RE_ANIO.search(texto))
            listada = page.page in paginas_listadas
            otra_seccion = self._RE_OTRA_SECCION.search(texto) is not None

            if tiene_marcador or (listada and not activo):
                if actual:
                    bloques.append("\n".join(actual))
                actual = [texto]
                activo = True
            elif activo and not otra_seccion:
                # Continuacion: sigue al F22 anterior, no trae su propio
                # año ni pertenece claramente a otra seccion.
                actual.append(texto)
            else:
                if actual:
                    bloques.append("\n".join(actual))
                actual = []
                activo = False

        if actual:
            bloques.append("\n".join(actual))
        return bloques

    def _detectar_anio(self, text: str) -> str | None:
        m = self._RE_ANIO.search(text)
        return m.group(1) if m else None

    def _extraer_datos(self, text: str, anio_tributario: str) -> AnnualTaxReturn:
        valores: dict[str, int] = {}
        for codigo, campo in self._CODIGO_MAPPING.items():
            # El SII a veces separa miles con puntos ("102.644.484") y a
            # veces no -- se acepta ambos formatos y se limpian los puntos
            # despues de capturar.
            patron = re.compile(rf"(?<!\d){re.escape(codigo)}\b\s+([^\d]*?)(-?\d[\d.]*)")
            match = patron.search(text)
            if not match:
                continue

            if codigo == "305" and not self._glosa_305_confiable(match.group(1)):
                # El formato viejo del SII ("Resultado Liquidación Impto
                # Rta", sin "ANUAL") produce montos que no cuadran con la
                # magnitud real de la empresa -- muy probablemente un
                # artefacto de columnas pegadas en la extraccion de texto,
                # no el valor real. Se prefiere omitir a mostrar un monto
                # que podria estar mal por varios ordenes de magnitud.
                continue

            crudo = match.group(2).rstrip(".").replace(".", "")
            if crudo not in ("", "-"):
                valores[campo] = int(crudo)

        observaciones = [
            mensaje
            for campo, mensaje in self._OBSERVACIONES_CAMPOS_FALTANTES.items()
            if campo not in valores
        ]
        if "impuesto_determinado" not in valores and re.search(
            r"305\s+Resultado\s+Liquidaci[oó]n\s+Impto", text, re.IGNORECASE
        ):
            observaciones.append(
                "Impuesto determinado no confiable en este formato de Formulario 22 (pendiente de revisión)"
            )

        return AnnualTaxReturn(
            anio_tributario=anio_tributario,
            observaciones=observaciones,
            **valores,
        )

    @staticmethod
    def _glosa_305_confiable(glosa: str) -> bool:
        """El formato viejo del SII abrevia la glosa como 'Impto Rta', y en
        la practica ese monto viene corrupto (artefacto de columnas
        pegadas en la extraccion). Cualquier otra redaccion (incluida la
        version corta sin abreviar) se considera confiable."""
        return "IMPTO RTA" not in glosa.upper()
