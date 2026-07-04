import re

class F22Parser:
    def __init__(self):
        # Mapeo estratégico de los códigos clave del SII
        self.codigo_mapping = {
            "628": "ingresos",
            "643": "renta_liquida_imponible",
            "645": "capital_propio_tributario",
            "142": "impuesto_determinado",
            "743": "ppm",
            "158": "base_imponible",
            "resultado_tributario": "resultado_tributario"
        }
        # Códigos que suelen aparecer pegados inmediatamente después de un monto
        self.codigos_ruido = ["630", "631", "637", "639", "643", "645", "647", "305", "142", "743", "929", "802"]

    def _limpiar_monto(self, monto_str: str) -> int:
        """
        Remueve los artefactos de concatenación del SII cuando un monto se fusiona 
        con el código numérico de la celda siguiente.
        """
        if not monto_str:
            return 0
            
        monto_limpio = monto_str.strip()
        
        # Si la cadena es sospechosamente larga (típicamente > 8 dígitos para pymes)
        # y termina en un código de formulario conocido, podamos los últimos 3 dígitos.
        if len(monto_limpio) >= 8:
            posible_codigo = monto_limpio[-3:]
            if posible_codigo in self.codigos_ruido:
                monto_limpio = monto_limpio[:-3]
                
        # Doble verificación por si se pegaron dos códigos consecutivos en formatos extremos
        if len(monto_limpio) >= 8:
            posible_codigo = monto_limpio[-3:]
            if posible_codigo in self.codigos_ruido:
                monto_limpio = monto_limpio[:-3]

        try:
            return int(monto_limpio)
        except ValueError:
            return 0

    def parse(self, extract_result, section_result) -> list:
        """
        Analiza el texto del F22 con soporte elástico, fallback total sobre extract_result
        y limpieza quirúrgica de artefactos de concatenación.
        """
        declaraciones = []
        text = ""

        # 1. Intentar usar la sección detectada por el pipeline
        if hasattr(section_result, 'text') and section_result.text:
            text = section_result.text
        
        # 2. FALLBACK: Si no hay sección, escaneamos el extract_result completo
        if not text and extract_result:
            paginas_f22 = []
            if hasattr(extract_result, 'pages') and extract_result.pages:
                for page in extract_result.pages:
                    page_text = getattr(page, 'text', '') or (page if isinstance(page, str) else '')
                    if page_text and any(kw in page_text.upper() for kw in ["FORM. 22", "FORMULARIO 22", "AÑO TRIBUTARIO", "ANIO TRIBUTARIO"]):
                        paginas_f22.append(page_text)
            
            if paginas_f22:
                text = "\n".join(paginas_f22)

        if not text:
            return declaraciones

        # --- DETECCIÓN ELÁSTICA DEL AÑO TRIBUTARIO ---
        match_anio = re.search(r"(?:AÑO TRIBUTARIO|ANIO TRIBUTARIO)\s*(\d{4})", text, flags=re.IGNORECASE)
        if match_anio:
            anio_tributario = match_anio.group(1)
        else:
            match_antiguo = re.search(r"(?:FORM\.\s*22|PERIODO|TRIBUTARIO)[^\d]*(\d{4})", text, flags=re.IGNORECASE)
            match_any_year = re.search(r"\b(201[5-9]|202[0-7])\b", text)
            anio_tributario = match_antiguo.group(1) if match_antiguo else (match_any_year.group(1) if match_any_year else "2019")

        data_f22 = {
            "anio_tributario": anio_tributario,
            "ingresos": 0,
            "renta_liquida_imponible": 0,
            "capital_propio_tributario": 0,
            "impuesto_determinado": 0,
            "ppm": 0,
            "creditos": 0,
            "perdidas": 0,
            "base_imponible": 0,
            "resultado_tributario": 0
        }

        # 3. Extracción por tokens con Limpieza Quirúrgica
        for codigo, campo in self.codigo_mapping.items():
            if codigo == "resultado_tributario":
                continue
            patron = re.compile(rf"{codigo}\s+[A-Za-zÁÉÍÓÚÑa-záéíóúñ\s\(\),ºª\.\/]+?\s+(\d+)")
            match = patron.search(text)
            if match:
                data_f22[campo] = self._limpiar_monto(match.group(1))

        # 4. Contingencias por proximidad de glosas de texto (Respaldo absoluto)
        if data_f22["ingresos"] == 0:
            match_ing = re.search(r"Ingresos del Giro\s+[^\d]*\s*(\d+)", text, flags=re.IGNORECASE)
            if match_ing: 
                data_f22["ingresos"] = self._limpiar_monto(match_ing.group(1))

        if data_f22["renta_liquida_imponible"] == 0:
            match_rli = re.search(r"(?:Renta Líquida Imponible|Renta Líquida \(o Pérdida\))\s+[^\d]*\s*(\d+)", text, flags=re.IGNORECASE)
            if match_rli:
                data_f22["renta_liquida_imponible"] = self._limpiar_monto(match_rli.group(1))

        if data_f22["capital_propio_tributario"] == 0:
            match_cpt = re.search(r"Capital Propio Tributario[^\d]*\s*(\d+)", text, flags=re.IGNORECASE)
            if match_cpt:
                data_f22["capital_propio_tributario"] = self._limpiar_monto(match_cpt.group(1))

        # 5. Capturar y Limpiar el Código 305 (Resultado de la Liquidación)
        match_305 = re.search(r"305\s+[A-Za-zÁÉÍÓÚÑa-záéíóúñ\s\(\),ºª\.\/]*?\s*(\d+)", text, flags=re.IGNORECASE)
        if not match_305:
            # Fallback si el número del código viene inmediatamente antes del monto sin glosa
            match_305 = re.search(r"\b305\s+(\d+)", text)
            
        if match_305:
            data_f22["resultado_tributario"] = self._limpiar_monto(match_305.group(1))

        declaraciones.append(data_f22)
        return declaraciones
