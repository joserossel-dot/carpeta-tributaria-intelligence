import re
from typing import Any

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
      1113 = Impuesto de Primera Categoría (IDPC 27% sobre RLI Cód. 1109/1690)
      305  = Resultado/Saldo Líquido a Pagar tras deducir PPM (Cód. 36/1904) y créditos
    """

    # Códigos para régimen 14A, ProPyme (14 D3, 14 D8) y formularios históricos
    # Jerarquía explícita v2.7:
    # CPT Negativo: 646 (Anverso actual), 1704 (Recuadro 14), 845 (histórico), 1546
    _CPT_NEGATIVO_CODES = ["646", "1704", "845", "1546"]
    # CPT Positivo: 1698 (Recuadro 14), 645 (Anverso actual), 844 (histórico 2017-2019), 1545, 1703, 1696
    _CPT_POSITIVO_CODES = ["1698", "645", "844", "1545", "1703", "1696"]
    _INGRESOS_CODES = ["1657", "1400", "1410", "628"]
    # RLI: 1694/1690 (Recuadro 12 RLI 14A), 1440/1580 (ProPyme 14D3/14D8), 1414, 1438, 643, 225, fallback 1109
    _RLI_CODES = ["1694", "1690", "1440", "1580", "1414", "1438", "643", "225", "1109"]
    _PERDIDAS_CODES = ["1695", "1450", "1706", "1143", "229"]
    _BASE_IMPONIBLE_CODES = ["1109", "1440", "1414", "1438"]
    _PPM_CODES = ["36", "849", "1904"]
    _CREDITOS_CODES = ["82", "626"]
    _IDPC_CODES = ["1113", "18"]
    _SALDO_LIQUIDACION_CODES = ["305", "90"]

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

    @staticmethod
    def _extract_raw_code(text: str, codigo: str) -> tuple[int | None, str]:
        """Extrae el valor numérico de un código SII específico, tolerando:
        - Códigos de 3 dígitos con cero inicial (ej. 0628)
        - Falta de espacio entre código y glosa (ej. 646Capital)
        - Distribución en 2 columnas intercaladas por pdfplumber (ej. 843 y 844 en la misma fila)
        - Continuación de glosa/monto en la línea siguiente
        - Glosas que contienen números descriptivos (ej. al 31 de diciembre, recuadro N° 14, art. 14)
        """
        lines = text.split("\n")
        adjusted_lines = []
        for line in lines:
            # Si en la misma línea aparecen dos códigos SII contiguos (ej. '843 Patrimonio financiero 1.752.776.382 844 C di a s...')
            # separamos la columna izquierda y derecha en líneas independientes para aislar estrictamente sus montos
            m_two_cols = re.search(r"^(.*?)(?:\s+)(\d{3,4})\s+([A-Za-zÁ-Úá-ú].*)$", line)
            if m_two_cols:
                col1 = m_two_cols.group(1).strip()
                code2 = m_two_cols.group(2)
                rest2 = m_two_cols.group(3).strip()
                if re.match(r"^\s*\d{3,4}\b", col1):
                    adjusted_lines.append(col1)
                    adjusted_lines.append(f"{code2} {rest2}")
                    continue
            adjusted_lines.append(line)

        clean_text = "\n".join(adjusted_lines)

        patron = re.compile(
            rf"(?:^|[^\d]|/\d{{4}}|\b)0?{re.escape(codigo)}(?:\s*|\b)([^\d]*?)\s*(-?[\d.,]+)(.*)"
        )
        match = patron.search(clean_text)
        if not match:
            return None, ""
        glosa = match.group(1).strip()
        raw_num = match.group(2)
        resto = match.group(3)

        # Si el número capturado forma parte de una fecha o texto de la glosa (ej. "31 de diciembre", "N° 14"),
        # continuar buscando la cifra tributaria real en el resto de la línea.
        while (
            (codigo in ("1113", "1904") and not any(c.isdigit() for c in raw_num))
            or re.search(r"(?:recuadro|n[°º]|art|art[ií]culo|inciso)\s*$", glosa, re.IGNORECASE)
            or re.match(r"^\s*(?:\)|de\s+[a-záéíóú]+|art\b|inciso\b|n[°º]\s*\d+)", resto, re.IGNORECASE)
            or (codigo in ("1113", "1904") and re.search(r"(-?\d{1,3}(?:\.\d{3})+|\b\d{4,}\b)", resto))
        ):
            m2 = re.search(r"(-?[\d.,]+)(.*)", resto)
            if m2:
                glosa = (glosa + " " + raw_num + " " + resto[: m2.start()]).strip()
                raw_num = m2.group(1)
                resto = m2.group(2)
            else:
                break

        # Si raw_num tiene pegado el código de la siguiente columna (ej: 1167358587647 Activo Inmovilizado)
        m_glue = re.match(r"^\s*([A-Za-zÁ-Úá-ú]{2,})", resto)
        if m_glue and len(raw_num) > 5 and raw_num.replace("-", "").isdigit():
            for code_len in (3, 4):
                cand_val = raw_num[:-code_len]
                if len(cand_val) >= 1:
                    raw_num = cand_val
                    break

        cleaned = raw_num.rstrip(".").replace(".", "").replace(",", ".").replace("−", "-")
        try:
            return int(float(cleaned)), glosa
        except (ValueError, TypeError):
            return None, glosa

    def _extraer_datos(self, text: str, anio_tributario: str) -> AnnualTaxReturn:
        valores: dict[str, Any] = {}

        # 1. Capital Propio Tributario (Positivo / Negativo)
        # Revisar códigos negativos primero
        cpt_val = None
        cpt_source = None
        for code in self._CPT_NEGATIVO_CODES:
            val, _ = self._extract_raw_code(text, code)
            if val is not None and val > 0:
                cpt_val = -abs(val)
                cpt_source = code
                break

        if cpt_val is None:
            for code in self._CPT_POSITIVO_CODES:
                val, _ = self._extract_raw_code(text, code)
                if val is not None and val != 0:
                    cpt_val = val
                    cpt_source = code
                    break

        if cpt_val is not None:
            valores["capital_propio_tributario"] = cpt_val
            valores["cpt_source_code"] = cpt_source

        # 2. Ingresos del Giro
        for code in self._INGRESOS_CODES:
            val, _ = self._extract_raw_code(text, code)
            if val is not None and val != 0:
                valores["ingresos"] = val
                valores["ingresos_source_code"] = code
                break

        # 3. Pérdidas Tributarias
        perdidas_val = None
        perdidas_source = None
        for code in self._PERDIDAS_CODES:
            val, _ = self._extract_raw_code(text, code)
            if val is not None and val > 0:
                perdidas_val = abs(val)
                perdidas_source = code
                break

        if perdidas_val is not None:
            valores["perdidas"] = perdidas_val

        # 4. Renta Líquida Imponible y Base Imponible
        rli_val = None
        rli_source = None
        val_1694, _ = self._extract_raw_code(text, "1694")
        val_1695, _ = self._extract_raw_code(text, "1695")
        if val_1694 is not None and val_1694 > 0:
            rli_val = val_1694
            rli_source = "1694"
            valores.pop("perdidas", None)
        elif val_1695 is not None and val_1695 > 0:
            # Regla crítica del parser F22: si existe Cód. 1695 > 0 y Cód. 1694 está vacío/cero,
            # la RLI del ejercicio es NEGATIVA (-abs(1695)), nunca tomar Cód. 1690 como positivo.
            rli_val = -abs(val_1695)
            rli_source = "1695"
        else:
            for code in self._RLI_CODES:
                if code in ("1694", "1695"):
                    continue
                val, _ = self._extract_raw_code(text, code)
                if val is not None and val != 0:
                    rli_val = val
                    rli_source = code
                    break

        if rli_val is not None:
            valores["renta_liquida_imponible"] = rli_val
            valores["rli_source_code"] = rli_source
            if rli_val < 0 and "perdidas" not in valores:
                valores["perdidas"] = abs(rli_val)
        elif perdidas_val is not None:
            valores["renta_liquida_imponible"] = -abs(perdidas_val)
            valores["rli_source_code"] = perdidas_source

        # Resultado Financiero (Cód. 1672)
        val_1672, _ = self._extract_raw_code(text, "1672")
        if val_1672 is not None:
            valores["resultado_tributario"] = val_1672

        for code in self._BASE_IMPONIBLE_CODES:
            val, _ = self._extract_raw_code(text, code)
            if val is not None and val != 0:
                valores["base_imponible"] = val
                break

        # 5. PPM y Créditos
        for code in self._PPM_CODES:
            val, _ = self._extract_raw_code(text, code)
            if val is not None and val != 0:
                valores["ppm"] = val
                valores["ppm_imputados"] = val
                break

        for code in self._CREDITOS_CODES:
            val, _ = self._extract_raw_code(text, code)
            if val is not None and val != 0:
                valores["creditos"] = val
                break

        # 6. IDPC determinado (Cód. 1113, 18)
        for code in self._IDPC_CODES:
            val_idpc, _ = self._extract_raw_code(text, code)
            if val_idpc is not None and val_idpc != 0:
                valores["idpc_determinado"] = val_idpc
                break

        # 7. Saldo de Liquidación Anual (Cód. 305, 90) e Impuesto Determinado
        # Nota técnica SII:
        # Cód. 1113: Impuesto de Primera Categoría (IDPC 27% régimen general 14A sobre RLI Cód. 1109/1690).
        # Cód. 305 / Cód. 90: Saldo Líquido a Pagar resultante de la liquidación anual tras deducir PPM (Cód. 36/1904) y créditos.
        val_305, glosa_305 = self._extract_raw_code(text, "305")
        if val_305 is not None and self._glosa_305_confiable(glosa_305):
            valores["impuesto_determinado"] = val_305
            valores["saldo_liquidacion_anual"] = val_305
        elif val_305 is not None:
            pass
        else:
            val_90, _ = self._extract_raw_code(text, "090")
            if val_90 is not None:
                valores["saldo_liquidacion_anual"] = val_90
                valores["impuesto_determinado"] = val_90

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

