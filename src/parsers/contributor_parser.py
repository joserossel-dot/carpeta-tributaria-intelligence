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

        pages = getattr(extract_result, "pages", None) or []
        full_text = "\n".join(p.text for p in pages if getattr(p, "text", None)) if pages else text

        primera_linea_domicilio, domicilio = self._extract_domicilio(text)
        comuna, region = self._extract_comuna_y_region(primera_linea_domicilio or domicilio, full_text)

        return Contributor(
            razon_social=self._clean(self._match(self._RE_RAZON_SOCIAL, text)),
            rut=self._clean_rut(self._match(self._RE_RUT, text)),
            fecha_generacion=self._clean(self._match(self._RE_FECHA_GENERACION, text)),
            fecha_inicio_actividades=self._clean(self._match(self._RE_FECHA_INICIO, text)),
            tipo_contribuyente=self._clean(self._match(self._RE_CATEGORIA, text)),
            regimen_tributario=self._clean(self._match(self._RE_REGIMEN, text)),
            domicilio=domicilio,
            comuna=comuna,
            region=region,
        )

    @staticmethod
    def anonymize_person_name(name: str | None) -> str:
        """Anonimiza nombres de personas naturales conforme a la Ley 21.719 de Protección de Datos Personales.

        Convierte nombres completos en iniciales + apellidos (ej. 'JUAN CARLOS PEREZ CASTILLO' -> 'J. PEREZ C.').
        """
        if not name or not str(name).strip():
            return ""
        parts = str(name).strip().split()
        if len(parts) == 1:
            return f"{parts[0][0].upper()}."
        elif len(parts) == 2:
            return f"{parts[0][0].upper()}. {parts[1].upper()}"
        elif len(parts) == 3:
            return f"{parts[0][0].upper()}. {parts[1].upper()} {parts[2][0].upper()}."
        else:
            return f"{parts[0][0].upper()}. {parts[-2].upper()} {parts[-1][0].upper()}."

    _CODIGO_53_TO_REGION = {
        1: "REGIÓN DE TARAPACÁ",
        2: "REGIÓN DE ANTOFAGASTA",
        3: "REGIÓN DE ATACAMA",
        4: "REGIÓN DE COQUIMBO",
        5: "REGIÓN DE VALPARAÍSO",
        6: "REGIÓN DE O'HIGGINS",
        7: "REGIÓN DEL MAULE",
        8: "REGIÓN DEL BIOBÍO",
        9: "REGIÓN DE LA ARAUCANÍA",
        10: "REGIÓN DE LOS LAGOS",
        11: "REGIÓN DE AYSÉN",
        12: "REGIÓN DE MAGALLANES",
        13: "METROPOLITANA DE SANTIAGO",
        14: "REGIÓN DE LOS RÍOS",
        15: "REGIÓN DE ARICA Y PARINACOTA",
        16: "REGIÓN DE ÑUBLE",
    }

    _COMUNA_TO_REGION = {
        # Región Metropolitana de Santiago
        "CERRILLOS": "METROPOLITANA DE SANTIAGO",
        "CERRO NAVIA": "METROPOLITANA DE SANTIAGO",
        "CONCHALI": "METROPOLITANA DE SANTIAGO",
        "CONCHALÍ": "METROPOLITANA DE SANTIAGO",
        "EL BOSQUE": "METROPOLITANA DE SANTIAGO",
        "ESTACION CENTRAL": "METROPOLITANA DE SANTIAGO",
        "ESTACIÓN CENTRAL": "METROPOLITANA DE SANTIAGO",
        "HUECHURABA": "METROPOLITANA DE SANTIAGO",
        "INDEPENDENCIA": "METROPOLITANA DE SANTIAGO",
        "LA CISTERNA": "METROPOLITANA DE SANTIAGO",
        "LA FLORIDA": "METROPOLITANA DE SANTIAGO",
        "LA GRANJA": "METROPOLITANA DE SANTIAGO",
        "LA PINTANA": "METROPOLITANA DE SANTIAGO",
        "LA REINA": "METROPOLITANA DE SANTIAGO",
        "LAS CONDES": "METROPOLITANA DE SANTIAGO",
        "LO BARNECHEA": "METROPOLITANA DE SANTIAGO",
        "LO ESPEJO": "METROPOLITANA DE SANTIAGO",
        "LO PRADO": "METROPOLITANA DE SANTIAGO",
        "MACUL": "METROPOLITANA DE SANTIAGO",
        "MAIPU": "METROPOLITANA DE SANTIAGO",
        "MAIPÚ": "METROPOLITANA DE SANTIAGO",
        "NUNOA": "METROPOLITANA DE SANTIAGO",
        "ÑUÑOA": "METROPOLITANA DE SANTIAGO",
        "PEDRO AGUIRRE CERDA": "METROPOLITANA DE SANTIAGO",
        "PENALOLEN": "METROPOLITANA DE SANTIAGO",
        "PEÑALOLEN": "METROPOLITANA DE SANTIAGO",
        "PEÑALOLÉN": "METROPOLITANA DE SANTIAGO",
        "PROVIDENCIA": "METROPOLITANA DE SANTIAGO",
        "PUDAHUEL": "METROPOLITANA DE SANTIAGO",
        "QUILICURA": "METROPOLITANA DE SANTIAGO",
        "QUINTA NORMAL": "METROPOLITANA DE SANTIAGO",
        "RECOLETA": "METROPOLITANA DE SANTIAGO",
        "RENCA": "METROPOLITANA DE SANTIAGO",
        "SAN JOAQUIN": "METROPOLITANA DE SANTIAGO",
        "SAN JOAQUÍN": "METROPOLITANA DE SANTIAGO",
        "SAN MIGUEL": "METROPOLITANA DE SANTIAGO",
        "SAN RAMON": "METROPOLITANA DE SANTIAGO",
        "SAN RAMÓN": "METROPOLITANA DE SANTIAGO",
        "SANTIAGO": "METROPOLITANA DE SANTIAGO",
        "VITACURA": "METROPOLITANA DE SANTIAGO",
        "PUENTE ALTO": "METROPOLITANA DE SANTIAGO",
        "PIRQUE": "METROPOLITANA DE SANTIAGO",
        "SAN JOSE DE MAIPO": "METROPOLITANA DE SANTIAGO",
        "SAN JOSÉ DE MAIPO": "METROPOLITANA DE SANTIAGO",
        "COLINA": "METROPOLITANA DE SANTIAGO",
        "LAMPA": "METROPOLITANA DE SANTIAGO",
        "TILTIL": "METROPOLITANA DE SANTIAGO",
        "SAN BERNARDO": "METROPOLITANA DE SANTIAGO",
        "BUIN": "METROPOLITANA DE SANTIAGO",
        "PAINE": "METROPOLITANA DE SANTIAGO",
        "CALERA DE TANGO": "METROPOLITANA DE SANTIAGO",
        "MELIPILLA": "METROPOLITANA DE SANTIAGO",
        "ALHUE": "METROPOLITANA DE SANTIAGO",
        "ALHUÉ": "METROPOLITANA DE SANTIAGO",
        "CURACAVI": "METROPOLITANA DE SANTIAGO",
        "CURACAVÍ": "METROPOLITANA DE SANTIAGO",
        "MARIA PINTO": "METROPOLITANA DE SANTIAGO",
        "MARÍA PINTO": "METROPOLITANA DE SANTIAGO",
        "SAN PEDRO": "METROPOLITANA DE SANTIAGO",
        "TALAGANTE": "METROPOLITANA DE SANTIAGO",
        "EL MONTE": "METROPOLITANA DE SANTIAGO",
        "ISLA DE MAIPO": "METROPOLITANA DE SANTIAGO",
        "PADRE HURTADO": "METROPOLITANA DE SANTIAGO",
        "PENAFLOR": "METROPOLITANA DE SANTIAGO",
        "PEÑAFLOR": "METROPOLITANA DE SANTIAGO",

        # Región del Biobío
        "CONCEPCION": "REGIÓN DEL BIOBÍO",
        "CONCEPCIÓN": "REGIÓN DEL BIOBÍO",
        "TALCAHUANO": "REGIÓN DEL BIOBÍO",
        "CHIGUAYANTE": "REGIÓN DEL BIOBÍO",
        "CORONEL": "REGIÓN DEL BIOBÍO",
        "HUALPEN": "REGIÓN DEL BIOBÍO",
        "HUALPÉN": "REGIÓN DEL BIOBÍO",
        "HUALQUI": "REGIÓN DEL BIOBÍO",
        "LOTA": "REGIÓN DEL BIOBÍO",
        "PENCO": "REGIÓN DEL BIOBÍO",
        "SAN PEDRO DE LA PAZ": "REGIÓN DEL BIOBÍO",
        "SANTA JUANA": "REGIÓN DEL BIOBÍO",
        "TOME": "REGIÓN DEL BIOBÍO",
        "TOMÉ": "REGIÓN DEL BIOBÍO",
        "LOS ANGELES": "REGIÓN DEL BIOBÍO",
        "LOS ÁNGELES": "REGIÓN DEL BIOBÍO",
        "CABRERO": "REGIÓN DEL BIOBÍO",
        "LAJA": "REGIÓN DEL BIOBÍO",
        "MULCHEN": "REGIÓN DEL BIOBÍO",
        "MULCHÉN": "REGIÓN DEL BIOBÍO",
        "NACIMIENTO": "REGIÓN DEL BIOBÍO",
        "NEGRETE": "REGIÓN DEL BIOBÍO",
        "QUILACO": "REGIÓN DEL BIOBÍO",
        "QUILLECO": "REGIÓN DEL BIOBÍO",
        "SAN ROSENDO": "REGIÓN DEL BIOBÍO",
        "SANTA BARBARA": "REGIÓN DEL BIOBÍO",
        "SANTA BÁRBARA": "REGIÓN DEL BIOBÍO",
        "TUCAPEL": "REGIÓN DEL BIOBÍO",
        "YUMBEL": "REGIÓN DEL BIOBÍO",
        "ALTO BIOBIO": "REGIÓN DEL BIOBÍO",
        "ALTO BIOBÍO": "REGIÓN DEL BIOBÍO",
        "LEBU": "REGIÓN DEL BIOBÍO",
        "ARAUCO": "REGIÓN DEL BIOBÍO",
        "CANETE": "REGIÓN DEL BIOBÍO",
        "CAÑETE": "REGIÓN DEL BIOBÍO",
        "CONTULMO": "REGIÓN DEL BIOBÍO",
        "CURANILAHUE": "REGIÓN DEL BIOBÍO",
        "LOS ALAMOS": "REGIÓN DEL BIOBÍO",
        "LOS ÁLAMOS": "REGIÓN DEL BIOBÍO",
        "TIRUA": "REGIÓN DEL BIOBÍO",
        "TIRÚA": "REGIÓN DEL BIOBÍO",
        "ANTUCO": "REGIÓN DEL BIOBÍO",

        # Región de Valparaíso
        "VALPARAISO": "REGIÓN DE VALPARAÍSO",
        "VALPARAÍSO": "REGIÓN DE VALPARAÍSO",
        "VINA DEL MAR": "REGIÓN DE VALPARAÍSO",
        "VIÑA DEL MAR": "REGIÓN DE VALPARAÍSO",
        "CONCON": "REGIÓN DE VALPARAÍSO",
        "CONCÓN": "REGIÓN DE VALPARAÍSO",
        "QUILPUE": "REGIÓN DE VALPARAÍSO",
        "QUILPUÉ": "REGIÓN DE VALPARAÍSO",
        "VILLA ALEMANA": "REGIÓN DE VALPARAÍSO",
        "LIMACHE": "REGIÓN DE VALPARAÍSO",
        "OLMUE": "REGIÓN DE VALPARAÍSO",
        "OLMUÉ": "REGIÓN DE VALPARAÍSO",
        "QUILLOTA": "REGIÓN DE VALPARAÍSO",
        "LA CALERA": "REGIÓN DE VALPARAÍSO",
        "LA CRUZ": "REGIÓN DE VALPARAÍSO",
        "HIJUELAS": "REGIÓN DE VALPARAÍSO",
        "NOGALES": "REGIÓN DE VALPARAÍSO",
        "SAN ANTONIO": "REGIÓN DE VALPARAÍSO",
        "CARTAGENA": "REGIÓN DE VALPARAÍSO",
        "EL QUISCO": "REGIÓN DE VALPARAÍSO",
        "EL TABO": "REGIÓN DE VALPARAÍSO",
        "SANTO DOMINGO": "REGIÓN DE VALPARAÍSO",
        "ALGARROBO": "REGIÓN DE VALPARAÍSO",
        "CASABLANCA": "REGIÓN DE VALPARAÍSO",
        "LOS ANDES": "REGIÓN DE VALPARAÍSO",
        "SAN FELIPE": "REGIÓN DE VALPARAÍSO",
        "LA LIGUA": "REGIÓN DE VALPARAÍSO",
        "CABILDO": "REGIÓN DE VALPARAÍSO",
        "ZAPALLAR": "REGIÓN DE VALPARAÍSO",
        "PAPUDO": "REGIÓN DE VALPARAÍSO",
        "PETORCA": "REGIÓN DE VALPARAÍSO",
        "PUCHUNCAVI": "REGIÓN DE VALPARAÍSO",
        "PUCHUNCAVÍ": "REGIÓN DE VALPARAÍSO",
        "QUINTERO": "REGIÓN DE VALPARAÍSO",
        "SANTA MARIA": "REGIÓN DE VALPARAÍSO",
        "SANTA MARÍA": "REGIÓN DE VALPARAÍSO",
        "PUTAENDO": "REGIÓN DE VALPARAÍSO",
        "CATEMU": "REGIÓN DE VALPARAÍSO",
        "LLAILLAY": "REGIÓN DE VALPARAÍSO",
        "PANQUEHUE": "REGIÓN DE VALPARAÍSO",
        "RINCONADA": "REGIÓN DE VALPARAÍSO",
        "CALLE LARGA": "REGIÓN DE VALPARAÍSO",
        "SAN ESTEBAN": "REGIÓN DE VALPARAÍSO",
        "ISLA DE PASCUA": "REGIÓN DE VALPARAÍSO",
        "JUAN FERNANDEZ": "REGIÓN DE VALPARAÍSO",
        "JUAN FERNÁNDEZ": "REGIÓN DE VALPARAÍSO",

        # Región de Antofagasta
        "ANTOFAGASTA": "REGIÓN DE ANTOFAGASTA",
        "CALAMA": "REGIÓN DE ANTOFAGASTA",
        "MEJILLONES": "REGIÓN DE ANTOFAGASTA",
        "TALTAL": "REGIÓN DE ANTOFAGASTA",
        "SIERRA GORDA": "REGIÓN DE ANTOFAGASTA",
        "TOCOPILLA": "REGIÓN DE ANTOFAGASTA",
        "MARIA ELENA": "REGIÓN DE ANTOFAGASTA",
        "MARÍA ELENA": "REGIÓN DE ANTOFAGASTA",
        "SAN PEDRO DE ATACAMA": "REGIÓN DE ANTOFAGASTA",
        "OLLAGUE": "REGIÓN DE ANTOFAGASTA",
        "OLLAGÜE": "REGIÓN DE ANTOFAGASTA",

        # Región de La Araucanía
        "TEMUCO": "REGIÓN DE LA ARAUCANÍA",
        "PADRE LAS CASAS": "REGIÓN DE LA ARAUCANÍA",
        "VILLARRICA": "REGIÓN DE LA ARAUCANÍA",
        "PUCON": "REGIÓN DE LA ARAUCANÍA",
        "PUCÓN": "REGIÓN DE LA ARAUCANÍA",
        "ANGOL": "REGIÓN DE LA ARAUCANÍA",
        "VICTORIA": "REGIÓN DE LA ARAUCANÍA",
        "LAUTARO": "REGIÓN DE LA ARAUCANÍA",
        "NUEVA IMPERIAL": "REGIÓN DE LA ARAUCANÍA",
        "CARAHUE": "REGIÓN DE LA ARAUCANÍA",
        "PITRUFQUEN": "REGIÓN DE LA ARAUCANÍA",
        "PITRUFQUÉN": "REGIÓN DE LA ARAUCANÍA",
        "LONCOCHE": "REGIÓN DE LA ARAUCANÍA",
        "COLLIPULLI": "REGIÓN DE LA ARAUCANÍA",
        "TRAIGUEN": "REGIÓN DE LA ARAUCANÍA",
        "TRAIGUÉN": "REGIÓN DE LA ARAUCANÍA",
        "CURACAUTIN": "REGIÓN DE LA ARAUCANÍA",
        "CURACAUTÍN": "REGIÓN DE LA ARAUCANÍA",
        "PUREN": "REGIÓN DE LA ARAUCANÍA",
        "PURÉN": "REGIÓN DE LA ARAUCANÍA",
        "RENAICO": "REGIÓN DE LA ARAUCANÍA",
        "GORBEA": "REGIÓN DE LA ARAUCANÍA",
        "FREIRE": "REGIÓN DE LA ARAUCANÍA",
        "TOLTEN": "REGIÓN DE LA ARAUCANÍA",
        "TOLTÉN": "REGIÓN DE LA ARAUCANÍA",
        "TEODORO SCHMIDT": "REGIÓN DE LA ARAUCANÍA",
        "SAAVEDRA": "REGIÓN DE LA ARAUCANÍA",
        "CHOLCHOL": "REGIÓN DE LA ARAUCANÍA",
        "GALVARINO": "REGIÓN DE LA ARAUCANÍA",
        "PERQUENCO": "REGIÓN DE LA ARAUCANÍA",
        "VILCUN": "REGIÓN DE LA ARAUCANÍA",
        "VILCÚN": "REGIÓN DE LA ARAUCANÍA",
        "CUNCO": "REGIÓN DE LA ARAUCANÍA",
        "MELIPEUCO": "REGIÓN DE LA ARAUCANÍA",
        "CURARREHUE": "REGIÓN DE LA ARAUCANÍA",
        "LONQUIMAY": "REGIÓN DE LA ARAUCANÍA",
        "LOS SAUCES": "REGIÓN DE LA ARAUCANÍA",
        "LUMACO": "REGIÓN DE LA ARAUCANÍA",
        "ERCILLA": "REGIÓN DE LA ARAUCANÍA",

        # Región de Los Lagos
        "PUERTO MONTT": "REGIÓN DE LOS LAGOS",
        "PUERTO VARAS": "REGIÓN DE LOS LAGOS",
        "OSORNO": "REGIÓN DE LOS LAGOS",
        "CASTRO": "REGIÓN DE LOS LAGOS",
        "ANCUD": "REGIÓN DE LOS LAGOS",
        "QUELLON": "REGIÓN DE LOS LAGOS",
        "QUELLÓN": "REGIÓN DE LOS LAGOS",
        "LLANQUIHUE": "REGIÓN DE LOS LAGOS",
        "FRUTILLAR": "REGIÓN DE LOS LAGOS",
        "CALBUCO": "REGIÓN DE LOS LAGOS",
        "LOS MUERMOS": "REGIÓN DE LOS LAGOS",
        "MAULLIN": "REGIÓN DE LOS LAGOS",
        "MAULLÍN": "REGIÓN DE LOS LAGOS",
        "COCHAMO": "REGIÓN DE LOS LAGOS",
        "COCHAMÓ": "REGIÓN DE LOS LAGOS",
        "FRESIA": "REGIÓN DE LOS LAGOS",
        "DALCAHUE": "REGIÓN DE LOS LAGOS",
        "CHONCHI": "REGIÓN DE LOS LAGOS",
        "QUINCHAO": "REGIÓN DE LOS LAGOS",
        "QUEMCHI": "REGIÓN DE LOS LAGOS",
        "CURACO DE VELEZ": "REGIÓN DE LOS LAGOS",
        "CURACO DE VÉLEZ": "REGIÓN DE LOS LAGOS",
        "PUQUELDON": "REGIÓN DE LOS LAGOS",
        "PUQUELDÓN": "REGIÓN DE LOS LAGOS",
        "QUEILEN": "REGIÓN DE LOS LAGOS",
        "QUEILÉN": "REGIÓN DE LOS LAGOS",
        "PURRANQUE": "REGIÓN DE LOS LAGOS",
        "RIO NEGRO": "REGIÓN DE LOS LAGOS",
        "RÍO NEGRO": "REGIÓN DE LOS LAGOS",
        "PUYEHUE": "REGIÓN DE LOS LAGOS",
        "PUERTO OCTAY": "REGIÓN DE LOS LAGOS",
        "SAN JUAN DE LA COSTA": "REGIÓN DE LOS LAGOS",
        "SAN PABLO": "REGIÓN DE LOS LAGOS",
        "CHAITEN": "REGIÓN DE LOS LAGOS",
        "CHAITÉN": "REGIÓN DE LOS LAGOS",
        "FUTALEUFU": "REGIÓN DE LOS LAGOS",
        "FUTALEUFÚ": "REGIÓN DE LOS LAGOS",
        "HUALAIHUE": "REGIÓN DE LOS LAGOS",
        "HUALAIHUÉ": "REGIÓN DE LOS LAGOS",
        "PALENA": "REGIÓN DE LOS LAGOS",

        # Región de O'Higgins
        "RANCAGUA": "REGIÓN DE O'HIGGINS",
        "MACHALI": "REGIÓN DE O'HIGGINS",
        "MACHALÍ": "REGIÓN DE O'HIGGINS",
        "GRANEROS": "REGIÓN DE O'HIGGINS",
        "MOSTAZAL": "REGIÓN DE O'HIGGINS",
        "CODEGUA": "REGIÓN DE O'HIGGINS",
        "DOÑIHUE": "REGIÓN DE O'HIGGINS",
        "DONIHUE": "REGIÓN DE O'HIGGINS",
        "COLTAUCO": "REGIÓN DE O'HIGGINS",
        "COINCO": "REGIÓN DE O'HIGGINS",
        "PEUMO": "REGIÓN DE O'HIGGINS",
        "PICHIDEGUA": "REGIÓN DE O'HIGGINS",
        "SAN VICENTE": "REGIÓN DE O'HIGGINS",
        "RENGO": "REGIÓN DE O'HIGGINS",
        "REQUINOA": "REGIÓN DE O'HIGGINS",
        "REQUÍNOA": "REGIÓN DE O'HIGGINS",
        "QUINTA DE TILCOCO": "REGIÓN DE O'HIGGINS",
        "MALLOA": "REGIÓN DE O'HIGGINS",
        "OLIVAR": "REGIÓN DE O'HIGGINS",
        "SAN FERNANDO": "REGIÓN DE O'HIGGINS",
        "CHIMBARONGO": "REGIÓN DE O'HIGGINS",
        "SANTA CRUZ": "REGIÓN DE O'HIGGINS",
        "NANCAGUA": "REGIÓN DE O'HIGGINS",
        "PALMILLA": "REGIÓN DE O'HIGGINS",
        "PERALILLO": "REGIÓN DE O'HIGGINS",
        "CHEPICA": "REGIÓN DE O'HIGGINS",
        "CHÉPICA": "REGIÓN DE O'HIGGINS",
        "LOLOL": "REGIÓN DE O'HIGGINS",
        "PUMANQUE": "REGIÓN DE O'HIGGINS",
        "PLACILLA": "REGIÓN DE O'HIGGINS",
        "PICHILEMU": "REGIÓN DE O'HIGGINS",
        "MARCHIHUE": "REGIÓN DE O'HIGGINS",
        "MARCHIGÜE": "REGIÓN DE O'HIGGINS",
        "LITUECHE": "REGIÓN DE O'HIGGINS",
        "LA ESTRELLA": "REGIÓN DE O'HIGGINS",
        "NAVIDAD": "REGIÓN DE O'HIGGINS",
        "PAREDONES": "REGIÓN DE O'HIGGINS",

        # Región del Maule
        "TALCA": "REGIÓN DEL MAULE",
        "CURICO": "REGIÓN DEL MAULE",
        "CURICÓ": "REGIÓN DEL MAULE",
        "LINARES": "REGIÓN DEL MAULE",
        "CONSTITUCION": "REGIÓN DEL MAULE",
        "CONSTITUCIÓN": "REGIÓN DEL MAULE",
        "SAN CLEMENTE": "REGIÓN DEL MAULE",
        "MAULE": "REGIÓN DEL MAULE",
        "SAN JAVIER": "REGIÓN DEL MAULE",
        "PARRAL": "REGIÓN DEL MAULE",
        "CAUQUENES": "REGIÓN DEL MAULE",
        "MOLINA": "REGIÓN DEL MAULE",
        "TENO": "REGIÓN DEL MAULE",
        "ROMERAL": "REGIÓN DEL MAULE",
        "RAUCO": "REGIÓN DEL MAULE",
        "SAGRADA FAMILIA": "REGIÓN DEL MAULE",
        "HUALANE": "REGIÓN DEL MAULE",
        "HUALANÉ": "REGIÓN DEL MAULE",
        "LICANTEN": "REGIÓN DEL MAULE",
        "LICANTÉN": "REGIÓN DEL MAULE",
        "VICHUQUEN": "REGIÓN DEL MAULE",
        "VICHUQUÉN": "REGIÓN DEL MAULE",
        "VILLA ALEGRE": "REGIÓN DEL MAULE",
        "YERBAS BUENAS": "REGIÓN DEL MAULE",
        "COLBUN": "REGIÓN DEL MAULE",
        "COLBÚN": "REGIÓN DEL MAULE",
        "LONGAVI": "REGIÓN DEL MAULE",
        "LONGAVÍ": "REGIÓN DEL MAULE",
        "RETIRO": "REGIÓN DEL MAULE",
        "CHANCO": "REGIÓN DEL MAULE",
        "PELLUHUE": "REGIÓN DEL MAULE",
        "EMPEDRADO": "REGIÓN DEL MAULE",
        "PENCAHUE": "REGIÓN DEL MAULE",
        "PELARCO": "REGIÓN DEL MAULE",
        "RIO CLARO": "REGIÓN DEL MAULE",
        "RÍO CLARO": "REGIÓN DEL MAULE",
        "CUREPTO": "REGIÓN DEL MAULE",
        "SAN RAFAEL": "REGIÓN DEL MAULE",

        # Región de Coquimbo
        "LA SERENA": "REGIÓN DE COQUIMBO",
        "COQUIMBO": "REGIÓN DE COQUIMBO",
        "OVALLE": "REGIÓN DE COQUIMBO",
        "ILLAPEL": "REGIÓN DE COQUIMBO",
        "VICUNA": "REGIÓN DE COQUIMBO",
        "VICUÑA": "REGIÓN DE COQUIMBO",
        "SALAMANCA": "REGIÓN DE COQUIMBO",
        "LOS VILOS": "REGIÓN DE COQUIMBO",
        "ANDACOLLO": "REGIÓN DE COQUIMBO",
        "COMBARBALA": "REGIÓN DE COQUIMBO",
        "COMBARBALÁ": "REGIÓN DE COQUIMBO",
        "MONTE PATRIA": "REGIÓN DE COQUIMBO",
        "PUNITAQUI": "REGIÓN DE COQUIMBO",
        "RIO HURTADO": "REGIÓN DE COQUIMBO",
        "RÍO HURTADO": "REGIÓN DE COQUIMBO",
        "CANELA": "REGIÓN DE COQUIMBO",
        "PAIHUANO": "REGIÓN DE COQUIMBO",
        "PAIGUANO": "REGIÓN DE COQUIMBO",
        "LA HIGUERA": "REGIÓN DE COQUIMBO",

        # Región de Ñuble
        "CHILLAN": "REGIÓN DE ÑUBLE",
        "CHILLÁN": "REGIÓN DE ÑUBLE",
        "CHILLAN VIEJO": "REGIÓN DE ÑUBLE",
        "CHILLÁN VIEJO": "REGIÓN DE ÑUBLE",
        "SAN CARLOS": "REGIÓN DE ÑUBLE",
        "BULNES": "REGIÓN DE ÑUBLE",
        "YUNGAY": "REGIÓN DE ÑUBLE",
        "QUILLON": "REGIÓN DE ÑUBLE",
        "QUILLÓN": "REGIÓN DE ÑUBLE",
        "COIHUECO": "REGIÓN DE ÑUBLE",
        "PINTO": "REGIÓN DE ÑUBLE",
        "SAN IGNACIO": "REGIÓN DE ÑUBLE",
        "EL CARMEN": "REGIÓN DE ÑUBLE",
        "PEMUCO": "REGIÓN DE ÑUBLE",
        "QUIRIHUE": "REGIÓN DE ÑUBLE",
        "COELEMU": "REGIÓN DE ÑUBLE",
        "TREHUACO": "REGIÓN DE ÑUBLE",
        "TREGUACO": "REGIÓN DE ÑUBLE",
        "PORTEZUELO": "REGIÓN DE ÑUBLE",
        "RANQUIL": "REGIÓN DE ÑUBLE",
        "RÁNQUIL": "REGIÓN DE ÑUBLE",
        "NINHUE": "REGIÓN DE ÑUBLE",
        "SAN NICOLAS": "REGIÓN DE ÑUBLE",
        "SAN NICOLÁS": "REGIÓN DE ÑUBLE",
        "SAN FABIAN": "REGIÓN DE ÑUBLE",
        "SAN FABIÁN": "REGIÓN DE ÑUBLE",
        "COBQUECURA": "REGIÓN DE ÑUBLE",
        "NIQUEN": "REGIÓN DE ÑUBLE",
        "ÑIQUÉN": "REGIÓN DE ÑUBLE",

        # Región de Los Ríos
        "VALDIVIA": "REGIÓN DE LOS RÍOS",
        "LA UNION": "REGIÓN DE LOS RÍOS",
        "LA UNIÓN": "REGIÓN DE LOS RÍOS",
        "RIO BUENO": "REGIÓN DE LOS RÍOS",
        "RÍO BUENO": "REGIÓN DE LOS RÍOS",
        "PANGUIPULLI": "REGIÓN DE LOS RÍOS",
        "PAILLACO": "REGIÓN DE LOS RÍOS",
        "LOS LAGOS": "REGIÓN DE LOS RÍOS",
        "MARIQUINA": "REGIÓN DE LOS RÍOS",
        "SAN JOSE DE LA MARIQUINA": "REGIÓN DE LOS RÍOS",
        "LANCO": "REGIÓN DE LOS RÍOS",
        "FUTRONO": "REGIÓN DE LOS RÍOS",
        "LAGO RANCO": "REGIÓN DE LOS RÍOS",
        "MAFIL": "REGIÓN DE LOS RÍOS",
        "MÁFIL": "REGIÓN DE LOS RÍOS",
        "CORRAL": "REGIÓN DE LOS RÍOS",

        # Región de Tarapacá
        "IQUIQUE": "REGIÓN DE TARAPACÁ",
        "ALTO HOSPICIO": "REGIÓN DE TARAPACÁ",
        "POZO ALMONTE": "REGIÓN DE TARAPACÁ",
        "PICA": "REGIÓN DE TARAPACÁ",
        "HUARA": "REGIÓN DE TARAPACÁ",
        "CAMINA": "REGIÓN DE TARAPACÁ",
        "CAMIÑA": "REGIÓN DE TARAPACÁ",
        "COLCHANE": "REGIÓN DE TARAPACÁ",

        # Región de Arica y Parinacota
        "ARICA": "REGIÓN DE ARICA Y PARINACOTA",
        "CAMARONES": "REGIÓN DE ARICA Y PARINACOTA",
        "PUTRE": "REGIÓN DE ARICA Y PARINACOTA",
        "GENERAL LAGOS": "REGIÓN DE ARICA Y PARINACOTA",

        # Región de Atacama
        "COPIAPO": "REGIÓN DE ATACAMA",
        "COPIAPÓ": "REGIÓN DE ATACAMA",
        "VALLENAR": "REGIÓN DE ATACAMA",
        "CALDERA": "REGIÓN DE ATACAMA",
        "TIERRA AMARILLA": "REGIÓN DE ATACAMA",
        "CHANARAL": "REGIÓN DE ATACAMA",
        "CHAÑARAL": "REGIÓN DE ATACAMA",
        "DIEGO DE ALMAGRO": "REGIÓN DE ATACAMA",
        "HUASCO": "REGIÓN DE ATACAMA",
        "FREIRINA": "REGIÓN DE ATACAMA",
        "ALTO DEL CARMEN": "REGIÓN DE ATACAMA",

        # Región de Aysén
        "COYHAIQUE": "REGIÓN DE AYSÉN",
        "COIHAIQUE": "REGIÓN DE AYSÉN",
        "AYSEN": "REGIÓN DE AYSÉN",
        "AYSÉN": "REGIÓN DE AYSÉN",
        "PUERTO AYSEN": "REGIÓN DE AYSÉN",
        "PUERTO AYSÉN": "REGIÓN DE AYSÉN",
        "CISNES": "REGIÓN DE AYSÉN",
        "CHILE CHICO": "REGIÓN DE AYSÉN",
        "COCHRANE": "REGIÓN DE AYSÉN",
        "RIO IBANEZ": "REGIÓN DE AYSÉN",
        "RÍO IBÁÑEZ": "REGIÓN DE AYSÉN",
        "O'HIGGINS": "REGIÓN DE AYSÉN",
        "OHIGGINS": "REGIÓN DE AYSÉN",
        "TORTEL": "REGIÓN DE AYSÉN",
        "GUAITECAS": "REGIÓN DE AYSÉN",
        "LAGO VERDE": "REGIÓN DE AYSÉN",

        # Región de Magallanes
        "PUNTA ARENAS": "REGIÓN DE MAGALLANES",
        "PUERTO NATALES": "REGIÓN DE MAGALLANES",
        "NATALES": "REGIÓN DE MAGALLANES",
        "PORVENIR": "REGIÓN DE MAGALLANES",
        "CABO DE HORNOS": "REGIÓN DE MAGALLANES",
        "PUERTO WILLIAMS": "REGIÓN DE MAGALLANES",
        "PRIMAVERA": "REGIÓN DE MAGALLANES",
        "TIMAUKEL": "REGIÓN DE MAGALLANES",
        "SAN GREGORIO": "REGIÓN DE MAGALLANES",
        "LAGUNA BLANCA": "REGIÓN DE MAGALLANES",
        "RIO VERDE": "REGIÓN DE MAGALLANES",
        "RÍO VERDE": "REGIÓN DE MAGALLANES",
        "ANTARTICA": "REGIÓN DE MAGALLANES",
        "ANTÁRTICA": "REGIÓN DE MAGALLANES",
    }
    _COMUNAS_RM = {k for k, v in _COMUNA_TO_REGION.items() if v == "METROPOLITANA DE SANTIAGO"}

    @classmethod
    def _extract_comuna_y_region(
        cls, domicilio: str | None, full_text: str | None = None
    ) -> tuple[str | None, str | None]:
        """Extrae comuna y región del domicilio del SII y/o del Cód. 53 (Región) del F22.
        Cuando termina en ', COMUNA, CIUDAD' (ej. '..., LO ESPEJO, SANTIAGO' o '..., CONCEPCION, CONCEPCION'),
        asigna la Comuna y la Región oficial respectiva.
        """
        if not domicilio:
            return None, None
        partes = [p.strip() for p in domicilio.split(",") if p.strip()]
        if not partes:
            return None, None

        comuna: str | None = None
        region: str | None = None

        if len(partes) == 1:
            comuna = partes[0]
        else:
            p_last = partes[-1].upper()
            p_penultimate = partes[-2].upper()

            if p_last == "SANTIAGO":
                if len(partes) >= 3 and p_penultimate != "SANTIAGO":
                    comuna = partes[-2]
                else:
                    comuna = "SANTIAGO"
                region = "METROPOLITANA DE SANTIAGO"
            elif p_last in ("METROPOLITANA", "RM", "REGION METROPOLITANA", "METROPOLITANA DE SANTIAGO"):
                comuna = partes[-2]
                region = "METROPOLITANA DE SANTIAGO"
            elif p_last in cls._COMUNA_TO_REGION:
                comuna = partes[-1]
                region = cls._COMUNA_TO_REGION[p_last]
            elif p_penultimate in cls._COMUNA_TO_REGION:
                comuna = partes[-2]
                region = cls._COMUNA_TO_REGION[p_penultimate]
            else:
                comuna = partes[-1]

        # Si aún no tenemos región, intentar resolver por comuna
        if comuna and not region:
            c_norm = comuna.upper()
            if c_norm in cls._COMUNA_TO_REGION:
                region = cls._COMUNA_TO_REGION[c_norm]

        # Cruce con Cód. 53 (Región) del F22 en caso de persistir sin región
        if not region and full_text:
            m53 = re.search(r"\b53\s+Regi[oó]n\s+(\d{1,2})\b", full_text, re.IGNORECASE)
            if not m53:
                m53 = re.search(r"C[oó]d(?:igo|\.)?\s*53[^\d]*(\d{1,2})\b", full_text, re.IGNORECASE)
            if m53:
                cod = int(m53.group(1))
                if cod in cls._CODIGO_53_TO_REGION:
                    region = cls._CODIGO_53_TO_REGION[cod]

        return comuna, region

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
        if domicilio:
            domicilio = re.sub(r"\s*null\s*,", ", ", domicilio, flags=re.IGNORECASE)
            domicilio = re.sub(r"\s+null\b", "", domicilio, flags=re.IGNORECASE)
            domicilio = re.sub(r"\b([a-z])\s+,", r"\1,", domicilio)
            domicilio = re.sub(r"\s{2,}", " ", domicilio).strip()
        if primera_linea:
            primera_linea = re.sub(r"\s*null\s*,", ", ", primera_linea, flags=re.IGNORECASE)
            primera_linea = re.sub(r"\s+null\b", "", primera_linea, flags=re.IGNORECASE)
            primera_linea = re.sub(r"\b([a-z])\s+,", r"\1,", primera_linea)
            primera_linea = re.sub(r"\s{2,}", " ", primera_linea).strip()
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
        return value.split("\n")[0].strip() or None

    @staticmethod
    def _clean_rut(value: str | None) -> str | None:
        if value is None:
            return None
        rut = re.sub(r"\s+", "", value.split("\n")[0])
        return rut.replace("−", "-").strip() or None

    @classmethod
    def _extract_comuna(cls, domicilio: str | None) -> str | None:
        comuna, _ = cls._extract_comuna_y_region(domicilio)
        return comuna
