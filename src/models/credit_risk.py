from pydantic import BaseModel


class ComposicionVentas(BaseModel):
    """Hecho, no indicador: se reporta el dato, no se califica.

    No hay evidencia empírica (ver sesión de diseño) de que el código 111
    (boletas) aparezca en el dataset disponible -- pct_boletas puede
    quedar en 0.0 simplemente porque el rubro no emite boletas, no porque
    el parser esté fallando. No usar este campo solo, sin cruzar con el
    giro, para inferir nada.
    """

    pct_facturado: float | None = None
    pct_boletas: float | None = None
    monto_facturado_estimado: int | None = None
    meses_evaluados: int = 0
    nota: str | None = None


class PostergacionesIva(BaseModel):
    """Hecho, no indicador: postergar IVA es un mecanismo legal de PYME,
    no una señal de riesgo por sí sola. Se reporta frecuencia y períodos,
    sin calificar."""

    meses_con_postergacion: int = 0
    total_meses_evaluados: int = 0
    periodos: list[str] = []


class Hechos(BaseModel):
    composicion_ventas: ComposicionVentas = ComposicionVentas()
    postergaciones_iva: PostergacionesIva = PostergacionesIva()


class MoraEfectiva(BaseModel):
    score: int | None = None
    meses_con_recargo: int = 0
    meses_con_remanente_credito: int = 0
    meses_evaluados: int = 0
    confianza: str = "sin_datos"
    criterio: str = (
        "distingue remanente de crédito fiscal (posición normal) de mora "
        "real (código 94 con recargo/interés)"
    )


class MargenVsGiro(BaseModel):
    score: int | None = None
    ratio_debito_credito_12m: float | None = None
    codigo_actividad: str | None = None
    descripcion_actividad: str | None = None
    ratio_promedio_sector: float | None = None
    n_empresas_referencia: int = 0
    confianza: str = "sin_datos"
    criterio: str = (
        "proxy de margen bruto (débito/crédito fiscal), no incluye "
        "remuneraciones; requiere benchmark propio por giro con muestra "
        "mínima antes de calificar con confianza alta"
    )


class RespaldoEstructural(BaseModel):
    score: int | None = None
    capital_propio_tributario: int | None = None
    cupo_solicitado: int | None = None
    cupo_referencia: int | None = None
    veces_cobertura: float | None = None
    confianza: str = "sin_datos"
    criterio: str = "CPT es proxy tributario, no liquidez real"


class Indicadores(BaseModel):
    mora_efectiva: MoraEfectiva = MoraEfectiva()
    margen_vs_giro: MargenVsGiro = MargenVsGiro()
    respaldo_estructural: RespaldoEstructural = RespaldoEstructural()


class CampoNoConfiable(BaseModel):
    campo: str
    motivo: str


class CalidadDatos(BaseModel):
    completitud_pct: float | None = None
    campos_no_confiables: list[CampoNoConfiable] = []
    meses_f29_faltantes: list[str] = []
    veredicto: str = "NO_EVALUADO"


class CaminoMitigacion(BaseModel):
    condicion: str
    aplica: bool
    resultado: str
    cupo_sugerido: int | None = None
    justificacion: str


class Decision(BaseModel):
    resultado_base: str | None = None
    evaluacion_referencial: str | None = None
    producto_evaluado: str | None = None
    cupo_maximo_sugerido: int | None = None
    cupo_aprobado: int | None = None
    linea_maxima_sugerida: int | None = None
    plazo_sugerido_dias: int | None = None
    garantia_exigida: str | None = None
    resguardo_comercial_sugerido: str | None = None
    protocolo_operativo: str | None = None
    memoria_calculo: dict | None = None
    hoja_ruta_comercial: list[str] = []
    caminos_mitigacion: list[CaminoMitigacion] = []


class CreditRiskResult(BaseModel):
    calidad_datos: CalidadDatos = CalidadDatos()
    hechos: Hechos = Hechos()
    indicadores: Indicadores = Indicadores()
    score_compuesto: int | None = None
    decision: Decision = Decision()
    alertas: list[str] = []
    fortalezas: list[str] = []
    banderas_rojas: list[str] = []
    dictamen_ejecutivo: str | None = None

    # Campos de Evaluación y Recomendación Referencial
    veredicto: str = "OBSERVADO"
    evaluacion_referencial: str = "OBSERVADO"
    score_crediticio: float = 0.0
    categoria_riesgo: str = "MEDIO"
    cupo_maximo_sugerido: int | None = None
    cupo_aprobado: int | None = None
    linea_maxima_sugerida: int | None = None
    plazo_sugerido_dias: int | None = None
    garantia_exigida: str | None = None
    resguardo_comercial_sugerido: str | None = None
    protocolo_operativo: str | None = None
    memoria_calculo: dict | None = None
    hoja_ruta_comercial: list[str] = []


