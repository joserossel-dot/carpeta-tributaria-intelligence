import re

class ContributorParser:
    def __init__(self):
        # Expresión regular elástica para capturar RUTs chilenos
        self.rut_pattern = re.compile(r"(\d{1,2}\.?\d{3}\.?\d{3}-[\dkK])")

    def parse(self, extract_result, section_result) -> dict:
        """
        Analiza la sección 'Conformación de la sociedad' y devuelve un DICCIONARIO
        compatible con el modelo Contributor para no romper la validación de Pydantic.
        """
        representatives = []
        
        # Extraemos el texto semántico
        text = ""
        if hasattr(section_result, 'text') and section_result.text:
            text = section_result.text
        elif hasattr(extract_result, 'text') and extract_result.text:
            text = extract_result.text
        elif isinstance(extract_result, str):
            text = extract_result
            
        if not text:
            return {} # Retornamos diccionario vacío en vez de lista para no romper Pydantic

        # Normalizar espacios
        clean_text = " ".join(text.split())
        
        # Acotar la búsqueda a la sección de interés
        start_keywords = ["CONFORMACIÓN DE LA SOCIEDAD", "CONFORMACION DE LA SOCIEDAD", "REPRESENTANTES LEGALES"]
        start_idx = -1
        for kw in start_keywords:
            if kw in clean_text.upper():
                start_idx = clean_text.upper().find(kw)
                break
                
        fragmento = clean_text[start_idx:start_idx + 4000] if start_idx != -1 else clean_text

        # Buscar todos los RUTs válidos
        ruts_encontrados = self.rut_pattern.findall(fragmento)
        
        if ruts_encontrados:
            # Procesar cada RUT por cercanía de texto
            for i, rut in enumerate(ruts_encontrados):
                pos_rut = fragmento.find(rut)
                bloque_nombre = fragmento[pos_rut + len(rut):pos_rut + 150]
                
                # Limpieza de ruido del SII
                bloque_nombre = re.sub(r"(REPRESENTANTE|LEGAL|SOCIO|ACCIONISTA|VIGENTE|FECHA|\bAL\b|\bDEL\b)", "", bloque_nombre, flags=re.IGNORECASE)
                
                if i + 1 < len(ruts_encontrados):
                    siguiente_rut = ruts_encontrados[i+1]
                    if siguiente_rut in bloque_nombre:
                        bloque_nombre = bloque_nombre.split(siguiente_rut)[0]
                
                match_nombre = re.search(r"([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{5,40})", bloque_nombre)
                nombre_socio = match_nombre.group(1).strip() if match_nombre else "Socio no identificado"

                match_part = re.search(r"(\d{1,3}(?:[.,]\d{1,2})?\s*%)", bloque_nombre)
                cargo_o_part = match_part.group(1).strip() if match_part else "Socio / Representante"

                representatives.append({
                    "rut": rut,
                    "nombre": nombre_socio,
                    "cargo": cargo_o_part,
                    "participacion": cargo_o_part
                })

        # SOLUCIÓN CRÍTICA: En lugar de retornar la lista pelada, retornamos un diccionario.
        # Metemos la lista dentro de la clave que tu modelo 'Contributor' probablemente espera
        # (puede ser 'representatives', 'partners' o 'socios'). Le damos las opciones comunes.
        return {
            "representatives": representatives,
            "partners": representatives,
            "socios": representatives
        }
