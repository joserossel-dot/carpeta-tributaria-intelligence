import math
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from src.credit.sector_benchmark import SectorBenchmark
from src.models.activity import Activity
from src.models.credit_risk import (
    CalidadDatos,
    CaminoMitigacion,
    CampoNoConfiable,
    ComposicionVentas,
    CreditRiskResult,
    Decision,
    Hechos,
    Indicadores,
    MargenVsGiro,
    MoraEfectiva,
    PilarScore,
    PostergacionesIva,
    RespaldoEstructural,
)
from src.models.tax_folder import TaxFolder
from src.utils.formatting import format_mclp

MESES_MINIMOS_PARA_SCORING = 6


def _floor_m100(val: float | int | Decimal | None) -> int:
    """Truncamiento/redondeo conservador hacia abajo al centenar de M$ ($100.000 CLP)."""
    if val is None or float(val) <= 0:
        return 0
    return int(math.floor(float(val) / 100_000.0) * 100_000)


_round_m100 = _floor_m100


class CreditRiskEngine:
    """Motor de decisión crediticia B2B v2.5.

    Evolución cuantitativa y comercial:
    1. Separación estricta entre Puntaje Tributario SII (comportamiento fiscal) y Riesgo Crediticio Comercial.
    2. Estructuración escalonada de línea: Línea Inicial Recomendada (Etapa 1 - 50%) vs. Línea Máxima Condicionada (Etapa 2).
    3. Modelo de Puntaje Tributario SII en 6 Pilares Objetivos (100 pts) y Filtro de Elegibilidad Tributaria.
    4. Integración de variables comerciales externas (Boletín Comercial Dicom/Equifax e Historial de Pago con Proveedor).
    5. Precisión conceptual en Memoria de Cálculo con Margen Tributario F29 Proxy y condición suspensiva por RLI.
    """

    def __init__(self, benchmark: SectorBenchmark | None = None):
        self.benchmark = benchmark or SectorBenchmark()

    def calculate(
        self,
        tax_folder: TaxFolder,
        cupo_solicitado: int | None = None,
        boletin_comercial: str | None = None,
        historial_pago: str | None = None,
    ) -> CreditRiskResult:
        boletin = boletin_comercial or "Pendiente de consulta (Condiciona línea)"
        historial = historial_pago or "Cliente nuevo (Sin historial previo)"

        calidad = self._evaluar_calidad_datos(tax_folder)
        hechos = self._extraer_hechos(tax_folder)
        vigencia = self._evaluar_vigencia_datos(tax_folder)
        conciliacion = self._calcular_conciliacion_f29_f22(tax_folder)
        bienes_raices = self._resumen_bienes_raices(tax_folder)
        rli_comprimida, alerta_rli = self._detectar_compresion_rli(tax_folder)

        if calidad.veredicto != "APTO_PARA_SCORING":
            return CreditRiskResult(
                calidad_datos=calidad,
                hechos=hechos,
                vigencia_datos=vigencia,
                conciliacion_f29_f22=conciliacion,
                bienes_raices_resumen=bienes_raices,
                variables_comerciales={
                    "boletin_comercial": boletin,
                    "historial_pago": historial,
                },
            )

        # Cálculo de cupo comercial autónomo (Pasos A-D)
        cupo_maximo, memoria, aval_obligatorio = self._calcular_cupo_autonomo(
            tax_folder, calidad, hechos
        )

        indicadores = self._calcular_indicadores(
            tax_folder, cupo_solicitado, cupo_maximo
        )
        desglose_score = self._calcular_desglose_score(
            tax_folder, calidad, hechos, indicadores, memoria, rli_comprimida, vigencia, conciliacion
        )
        score_compuesto = self._componer_score(indicadores, desglose_score)

        # Filtro de Elegibilidad Tributaria (Etapa 1)
        mora_12m = indicadores.mora_efectiva.meses_con_recargo if indicadores.mora_efectiva else 0
        filtro_elegibilidad = self._calcular_filtro_elegibilidad(
            tax_folder, calidad, mora_12m, conciliacion
        )

        decision = self._decidir(
            hechos,
            indicadores,
            score_compuesto,
            cupo_solicitado,
            cupo_maximo,
            memoria,
            aval_obligatorio,
            tax_folder=tax_folder,
            rli_comprimida=rli_comprimida,
            boletin_comercial=boletin,
            historial_pago=historial,
        )
        decision.desglose_score = desglose_score
        decision.vigencia_datos = vigencia
        decision.conciliacion_f29_f22 = conciliacion
        decision.bienes_raices_resumen = bienes_raices
        decision.filtro_elegibilidad = filtro_elegibilidad

        alertas, fortalezas, banderas_rojas = self._alertas_y_fortalezas(
            hechos, indicadores, memoria, calidad
        )
        if alerta_rli:
            alertas.insert(0, alerta_rli)
            banderas_rojas.insert(0, alerta_rli)
        if vigencia.get("alerta"):
            alertas.append(vigencia["alerta"])

        dictamen = self._generar_dictamen_ejecutivo(
            tax_folder, score_compuesto, decision, memoria, banderas_rojas
        )

        veredicto = decision.evaluacion_referencial or decision.resultado_base or "OBSERVADO"
        score_val = float(score_compuesto) if score_compuesto is not None else 0.0
        clasif_riesgo = decision.clasificacion_riesgo or "MODERADO"
        cat_riesgo = (
            "BAJO"
            if "BAJO" in clasif_riesgo
            else ("ALTO" if "ALTO" in clasif_riesgo else "MEDIO")
        )

        return CreditRiskResult(
            calidad_datos=calidad,
            hechos=hechos,
            indicadores=indicadores,
            score_compuesto=score_compuesto,
            desglose_score=desglose_score,
            vigencia_datos=vigencia,
            conciliacion_f29_f22=conciliacion,
            bienes_raices_resumen=bienes_raices,
            filtro_elegibilidad=filtro_elegibilidad,
            decision=decision,
            alertas=alertas,
            fortalezas=fortalezas,
            banderas_rojas=banderas_rojas,
            dictamen_ejecutivo=dictamen,
            veredicto=veredicto,
            evaluacion_referencial=veredicto,
            clasificacion_riesgo=clasif_riesgo,
            desempeno_tributario_texto=decision.desempeno_tributario_texto or "Desempeño Tributario Medio",
            score_crediticio=score_val,
            categoria_riesgo=cat_riesgo,
            cupo_maximo_sugerido=decision.cupo_maximo_sugerido,
            cupo_aprobado=decision.cupo_aprobado,
            linea_maxima_sugerida=decision.linea_maxima_condicionada,
            linea_inicial_sugerida=decision.linea_inicial_sugerida,
            linea_maxima_condicionada=decision.linea_maxima_condicionada,
            plazo_sugerido_dias=decision.plazo_sugerido_dias,
            plazo_inicial_sugerido=decision.plazo_inicial_sugerido,
            condicion_escalamiento=decision.condicion_escalamiento,
            garantia_exigida=decision.garantia_exigida,
            resguardo_comercial_sugerido=decision.resguardo_comercial_sugerido,
            protocolo_operativo=decision.protocolo_operativo,
            memoria_calculo=decision.memoria_calculo,
            hoja_ruta_comercial=decision.hoja_ruta_comercial,
            variables_comerciales={
                "boletin_comercial": boletin,
                "historial_pago": historial,
            },
        )

    # ------------------------------------------------------------------
    # Calidad de datos y detección de lagunas
    # ------------------------------------------------------------------
    def _evaluar_calidad_datos(self, tax_folder: TaxFolder) -> CalidadDatos:
        campos_no_confiables = [
            CampoNoConfiable(campo=f"f22.{f.anio_tributario}.{obs_campo}", motivo=obs)
            for f in tax_folder.f22
            for obs in f.observaciones
            for obs_campo in [self._campo_desde_observacion(obs)]
        ]

        # Detección cronológica de meses ausentes ("lagunas")
        meses_faltantes = self._detectar_meses_faltantes(tax_folder)
        if meses_faltantes:
            campos_no_confiables.append(
                CampoNoConfiable(
                    campo="f29.continuidad",
                    motivo=f"Se detectaron {len(meses_faltantes)} meses sin declaración: {', '.join(meses_faltantes[:4])}"
                    + ("..." if len(meses_faltantes) > 4 else ""),
                )
            )

        meses_f29 = len(tax_folder.monthly_taxes)
        tiene_cpt = any(f.capital_propio_tributario is not None for f in tax_folder.f22)

        checks = {
            "contribuyente": tax_folder.contributor is not None
            and tax_folder.contributor.razon_social is not None,
            "f29_suficientes": meses_f29 >= MESES_MINIMOS_PARA_SCORING,
            "f22_con_cpt": tiene_cpt,
        }
        completitud_pct = round(100 * sum(checks.values()) / len(checks), 1)

        if checks["f29_suficientes"] and checks["contribuyente"]:
            veredicto = "APTO_PARA_SCORING"
        else:
            veredicto = "DATOS_INSUFICIENTES"

        return CalidadDatos(
            completitud_pct=completitud_pct,
            campos_no_confiables=campos_no_confiables,
            meses_f29_faltantes=meses_faltantes,
            veredicto=veredicto,
        )

    @staticmethod
    def _detectar_meses_faltantes(tax_folder: TaxFolder) -> list[str]:
        periodos_presentes = set(
            f.periodo for f in tax_folder.f29 if f and f.periodo and len(f.periodo) == 7
        )
        if len(periodos_presentes) < 2:
            return []

        sorted_p = sorted(periodos_presentes)
        try:
            sy, sm = int(sorted_p[0][:4]), int(sorted_p[0][5:7])
            ey, em = int(sorted_p[-1][:4]), int(sorted_p[-1][5:7])
        except (ValueError, IndexError):
            return []

        faltantes: list[str] = []
        cy, cm = sy, sm
        while (cy < ey) or (cy == ey and cm <= em):
            p_str = f"{cy:04d}-{cm:02d}"
            if p_str not in periodos_presentes:
                faltantes.append(p_str)
            cm += 1
            if cm > 12:
                cm = 1
                cy += 1
        return faltantes

    @staticmethod
    def _campo_desde_observacion(observacion: str) -> str:
        if observacion.startswith(("No se encontró", "No se encontraron")):
            return (
                observacion.replace("No se encontró", "")
                .replace("No se encontraron", "")
                .strip()
            )
        if "Impuesto determinado" in observacion:
            return "Impuesto determinado"
        return observacion[:40].strip()

    @staticmethod
    def _detectar_compresion_rli(tax_folder: TaxFolder) -> tuple[bool, str | None]:
        f22_validos = sorted(
            [f for f in tax_folder.f22 if f.anio_tributario],
            key=lambda f: f.anio_tributario or "",
            reverse=True,
        )
        if not f22_validos:
            return False, None

        ultimo = f22_validos[0]
        ingresos = ultimo.ingresos or 0
        rli = ultimo.renta_liquida_imponible

        # Caso 1: Ingresos positivos pero RLI <= 0 (o RLI es 0 con ventas millonarias)
        if ingresos > 0 and rli is not None and rli <= 0:
            ing_m = format_mclp(ingresos)
            rli_m = format_mclp(rli)
            msg = (
                f"Alerta de Rentabilidad Tributaria / Condición Suspensiva Documental: "
                f"Compresión severa de RLI en último F22 (AT {ultimo.anio_tributario}). "
                f"Ingresos: {ing_m} vs RLI: {rli_m} (Margen RLI 0%). "
                "Se exige Balance de 8 Columnas reciente para aclarar la causa de la RLI nula "
                "(depreciación, pérdidas de arrastre, corrección monetaria o bajo margen) "
                "antes de autorizar el escalamiento de Línea Inicial a Línea Máxima."
            )
            return True, msg

        # Caso 2: Caída de RLI > 70% respecto al año tributario anterior
        if len(f22_validos) >= 2:
            anterior = f22_validos[1]
            rli_ant = anterior.renta_liquida_imponible
            if rli_ant and rli_ant > 0 and rli is not None:
                caida = (rli - rli_ant) / rli_ant
                if caida < -0.70:
                    pct_caida = abs(caida) * 100
                    rli_m = format_mclp(rli)
                    ant_m = format_mclp(rli_ant)
                    msg = (
                        f"Alerta de Rentabilidad Tributaria: Caída de RLI de {pct_caida:.1f}% en F22 "
                        f"(AT {ultimo.anio_tributario}: {rli_m} vs AT {anterior.anio_tributario}: {ant_m}). "
                        "Se sugiere solicitar Balance de 8 Columnas reciente para validar margen real."
                    )
                    return True, msg

        return False, None

    @staticmethod
    def _calcular_filtro_elegibilidad(
        tax_folder: TaxFolder,
        calidad: CalidadDatos,
        mora: int,
        conciliacion: dict[str, Any] | None,
    ) -> list[dict[str, str]]:
        c = getattr(tax_folder, "contributor", None)
        rut = getattr(c, "rut", None) or "—"
        inicio_act = getattr(c, "fecha_inicio_actividades", None) or getattr(c, "inicio_actividades", None)
        rep_names = []
        if getattr(tax_folder, "representatives", None):
            for r in tax_folder.representatives:
                nom = getattr(r, "nombre", None) or (r.get("nombre") if isinstance(r, dict) else None)
                if nom and str(nom).strip():
                    rep_names.append(str(nom).strip())

        n_meses = len(tax_folder.monthly_taxes) or len(tax_folder.f29)
        lagunas = len(calidad.meses_f29_faltantes)

        return [
            {
                "parametro": "RUT e Inicio de Actividades Vigente",
                "estado": "CUMPLE" if rut != "—" else "OBSERVADO",
                "detalle": f"RUT {rut} con inicio registrado ({inicio_act or 'Vigente'})" if rut != "—" else "Sin RUT validado",
            },
            {
                "parametro": "Representantes Legales Identificados",
                "estado": "CUMPLE" if rep_names else "OBSERVADO",
                "detalle": f"{len(rep_names)} representante(s) registrado(s)" if rep_names else "Sin representantes registrados en carpeta",
            },
            {
                "parametro": "Continuidad F29 Reciente",
                "estado": "CUMPLE" if lagunas == 0 and n_meses >= 6 else "OBSERVADO",
                "detalle": f"{n_meses} meses sin lagunas tributarias" if lagunas == 0 else f"{lagunas} mes(es) de omisión detectados",
            },
            {
                "parametro": "Mora Fiscal Crítica (Cód. 94)",
                "estado": "CUMPLE" if mora <= 1 else "OBSERVADO",
                "detalle": "Cumplimiento oportuno de IVA" if mora <= 1 else f"{mora} meses con recargo por mora",
            },
            {
                "parametro": "Coherencia F29 vs F22",
                "estado": "CUMPLE" if (not conciliacion or conciliacion.get("diferencia_pct", 0) <= 15.0) else "OBSERVADO",
                "detalle": conciliacion.get("estado", "Sin declaraciones F22 concurrentes") if conciliacion else "Sin declaraciones F22 concurrentes",
            },
        ]

    @staticmethod
    def _evaluar_vigencia_datos(tax_folder: TaxFolder) -> dict[str, Any]:
        c = getattr(tax_folder, "contributor", None)
        fecha_emision_raw = getattr(c, "fecha_generacion", None) if c else None

        sorted_f29 = sorted(tax_folder.f29, key=lambda f: f.periodo or "")
        sorted_mt = sorted(tax_folder.monthly_taxes, key=lambda m: m.periodo or "")
        ultimo_periodo = (
            sorted_f29[-1].periodo
            if sorted_f29 and sorted_f29[-1].periodo
            else (sorted_mt[-1].periodo if sorted_mt and sorted_mt[-1].periodo else "No informado")
        )

        emision_y, emision_m = 2026, 1
        if fecha_emision_raw:
            try:
                date_part = str(fecha_emision_raw).strip().split()[0]
                if "/" in date_part:
                    p = date_part.split("/")
                    if len(p) == 3:
                        emision_m, emision_y = int(p[1]), int(p[2])
                elif "-" in date_part:
                    p = date_part.split("-")
                    if len(p) == 3:
                        if len(p[0]) == 4:
                            emision_y, emision_m = int(p[0]), int(p[1])
                        else:
                            emision_m, emision_y = int(p[1]), int(p[2])
            except (ValueError, IndexError):
                pass

        meses_desfase = 0
        if ultimo_periodo and len(ultimo_periodo) == 7 and "-" in ultimo_periodo:
            try:
                ult_y, ult_m = int(ultimo_periodo[:4]), int(ultimo_periodo[5:7])
                meses_desfase = max(0, (emision_y - ult_y) * 12 + (emision_m - ult_m))
            except (ValueError, IndexError):
                pass

        if meses_desfase <= 2:
            nivel = "ALTA"
            alerta = None
        elif meses_desfase <= 4:
            nivel = "MEDIA"
            alerta = None
        else:
            nivel = "BAJA"
            alerta = (
                f"Alerta de Vigencia: Carpeta tributaria con desfase de {meses_desfase} meses (> 4 meses). "
                f"Se sugiere solicitar carpeta tributaria actualizada."
            )

        return {
            "fecha_emision": fecha_emision_raw or "No informada",
            "ultimo_periodo": ultimo_periodo,
            "meses_desfase": meses_desfase,
            "nivel_confianza": nivel,
            "alerta": alerta,
        }

    @staticmethod
    def _calcular_conciliacion_f29_f22(tax_folder: TaxFolder) -> dict[str, Any] | None:
        f22_con_ingresos = sorted(
            [f for f in tax_folder.f22 if f.anio_tributario and f.ingresos and f.ingresos > 0],
            key=lambda f: f.anio_tributario or "",
            reverse=True,
        )
        if not f22_con_ingresos:
            return None

        for f22_item in f22_con_ingresos:
            try:
                at = int(f22_item.anio_tributario)
                ac = at - 1
            except (ValueError, TypeError):
                continue

            prefijo = f"{ac}-"
            meses_ac = [
                mt for mt in tax_folder.monthly_taxes
                if mt.periodo and mt.periodo.startswith(prefijo)
            ]
            if len(meses_ac) >= 6:
                ventas_f29 = sum(mt.total_ventas or Decimal("0") for mt in meses_ac)
                ingresos_f22 = f22_item.ingresos
                dif_monto = abs(int(ventas_f29) - ingresos_f22)
                dif_pct = round(dif_monto / float(ingresos_f22) * 100.0, 1) if ingresos_f22 else 0.0

                if dif_pct <= 10.0:
                    estado = "CONCILIADO (< 10% dif.)"
                elif dif_pct <= 15.0:
                    estado = "TOLERANCIA ACEPTABLE (10-15% dif.)"
                else:
                    estado = "DESVIACIÓN RELEVANTE (> 15% dif.)"

                v_str = format_mclp(ventas_f29)
                i_str = format_mclp(ingresos_f22)
                detalle = (
                    f"Ventas F29 año comercial {ac} ({v_str}) vs Ingresos F22 AT {at} ({i_str}) "
                    f"— Diferencia: {dif_pct}% ({estado})."
                )

                return {
                    "anio_tributario": str(at),
                    "anio_comercial": str(ac),
                    "meses_f29_contabilizados": len(meses_ac),
                    "ventas_f29_anual": int(ventas_f29),
                    "ingresos_f22": int(ingresos_f22),
                    "diferencia_monto": int(dif_monto),
                    "diferencia_pct": dif_pct,
                    "estado": estado,
                    "detalle": detalle,
                }
        return None

    @staticmethod
    def _resumen_bienes_raices(tax_folder: TaxFolder) -> str:
        props = getattr(tax_folder, "properties", []) or []
        if props:
            return f"Registra {len(props)} bien(es) raíz(ces) en la carpeta tributaria"
        return "No registra bienes raíces en carpeta"

    # ------------------------------------------------------------------
    # Hechos (sin calificar)
    # ------------------------------------------------------------------
    def _extraer_hechos(self, tax_folder: TaxFolder) -> Hechos:
        return Hechos(
            composicion_ventas=self._composicion_ventas(tax_folder),
            postergaciones_iva=self._postergaciones_iva(tax_folder),
        )

    @staticmethod
    def _composicion_ventas(tax_folder: TaxFolder) -> ComposicionVentas:
        facturado = 0
        boletas = 0
        for f29 in tax_folder.f29:
            for det in f29.detalles:
                if det.codigo == "502":
                    facturado += _parse_monto(det.valor)
                elif det.codigo == "111":
                    boletas += _parse_monto(det.valor)

        total = facturado + boletas
        nota = None
        if boletas == 0 and facturado > 0:
            nota = (
                "sin código 111 (boletas) detectado -- giro predominantemente B2B facturado"
            )

        return ComposicionVentas(
            pct_facturado=round(facturado / total, 4) if total else None,
            pct_boletas=round(boletas / total, 4) if total else None,
            monto_facturado_estimado=facturado or None,
            meses_evaluados=len(tax_folder.f29),
            nota=nota,
        )

    @staticmethod
    def _postergaciones_iva(tax_folder: TaxFolder) -> PostergacionesIva:
        periodos = []
        for f29 in tax_folder.f29:
            for det in f29.detalles:
                if det.codigo in ("779", "755", "756") and _parse_monto(det.valor) > 0:
                    periodos.append(f29.periodo)
                    break

        return PostergacionesIva(
            meses_con_postergacion=len(periodos),
            total_meses_evaluados=len(tax_folder.f29),
            periodos=periodos,
        )

    # ------------------------------------------------------------------
    # Algoritmo Determinista de Asignación de Cupo Comercial (Pasos A-D)
    # ------------------------------------------------------------------
    def _calcular_cupo_autonomo(
        self, tax_folder: TaxFolder, calidad: CalidadDatos, hechos: Hechos
    ) -> tuple[int, dict[str, Any], bool]:
        ma = tax_folder.monthly_analysis

        # Paso A: Base de Absorción de Compras sobre los 12 meses más recientes
        sorted_mt = sorted(tax_folder.monthly_taxes, key=lambda m: m.periodo or "")
        last_12_mt = sorted_mt[-12:] if len(sorted_mt) >= 12 else sorted_mt
        periodo_inicio = last_12_mt[0].periodo if last_12_mt else ""
        periodo_fin = last_12_mt[-1].periodo if last_12_mt else ""

        compras_op_sum = sum(
            float(mt.compras_operacionales if mt.compras_operacionales is not None else (mt.compras or Decimal("0")))
            for mt in last_12_mt
        )
        prom_compras_op_12m = (compras_op_sum / len(last_12_mt)) if last_12_mt else (
            float(ma.promedio_compras_operacionales_12m or ma.promedio_compras_mensual or Decimal("0")) if ma else 0.0
        )

        ventas_sum = sum(float(mt.total_ventas or Decimal("0")) for mt in last_12_mt)
        prom_ventas_12m = (ventas_sum / len(last_12_mt)) if last_12_mt else (
            float(ma.promedio_ventas_mensual or Decimal("0")) if ma else 0.0
        )
        ventas_u12 = ventas_sum if last_12_mt else (float(ma.ventas_ultimos_12 or Decimal("0")) if ma else 0.0)
        compras_u12 = compras_op_sum if last_12_mt else (prom_compras_op_12m * 12)

        # Tratamiento de empresas de giro exento, servicios o rentistas (compras < 15% ventas)
        es_servicios_o_exento = (
            (ventas_u12 > 0 and compras_u12 < 0.15 * ventas_u12)
            or (ma is not None and getattr(ma, "costo_operativo_proxy_aplica", False))
            or prom_compras_op_12m == 0
        )

        castigos: list[str] = []

        if es_servicios_o_exento and prom_ventas_12m > 0:
            if ma and getattr(ma, "promedio_costo_operativo_proxy_12m", None):
                c_base = float(ma.promedio_costo_operativo_proxy_12m)
            else:
                c_base = max(0.30 * prom_ventas_12m, prom_compras_op_12m)
            castigos.append(f"Empresa de servicios/rentas/exenta: Base calibrada con Costo Operativo Proxy (${c_base:,.0f} CLP/mes)")
        elif prom_compras_op_12m > 0:
            c_base = prom_compras_op_12m
        else:
            c_base = 0.30 * prom_ventas_12m if prom_ventas_12m > 0 else 0.0

        # Paso B: Techo Operativo (8% de compras mensuales para crédito proveedor v2.2/v2.3)
        techo_operativo = c_base * 0.08

        # Spread Operacional Tributario F29 = Ventas Netas Mensuales Promedio - Compras Op. Mensuales Promedio
        spread_operacional_f29 = max(0.0, prom_ventas_12m - c_base)

        # Paso B2: Freno por Absorción Operacional
        # Cuando exista RLI positiva en el último F22, calcular como:
        # min(15% del Spread Operacional Tributario F29, 25% de la RLI Mensualizada F22)
        # Si no hay F22 o RLI <= 0, usar 12% del Spread Operacional F29 con penalización.
        ultimo_f22 = None
        if tax_folder.f22:
            sorted_f22 = sorted(tax_folder.f22, key=lambda f: f.anio_tributario or "", reverse=True)
            if sorted_f22:
                ultimo_f22 = sorted_f22[0]

        rli_val = ultimo_f22.renta_liquida_imponible if ultimo_f22 else None
        rli_mensualizada = (float(rli_val) / 12.0) if (rli_val is not None and rli_val > 0) else None

        if rli_mensualizada is not None and rli_mensualizada > 0:
            freno_flujo = min(0.15 * spread_operacional_f29, 0.25 * rli_mensualizada)
            glosa_b2 = f"min(15% Spread F29: ${0.15 * spread_operacional_f29:,.0f}, 25% RLI Mensualizada: ${0.25 * rli_mensualizada:,.0f})"
        else:
            freno_flujo = 0.12 * spread_operacional_f29
            glosa_b2 = f"12% Spread Operacional F29 penalizado (${freno_flujo:,.0f})"

        # El cupo base no puede superar el freno de absorción operacional
        techo_con_flujo = min(techo_operativo, freno_flujo)
        if freno_flujo < techo_operativo:
            castigos.append(
                f"Freno por Absorción Operacional ({glosa_b2}): "
                f"reduce techo de compras de ${techo_operativo:,.0f} a ${freno_flujo:,.0f}"
            )

        # Paso C: Factor de Castigo por Riesgo (Phi)
        phi = 1.0

        # 1. Variación de ventas 3M vs 12M con validación YoY para descartar estacionalidad
        var_ventas_3m = float(ma.variacion_ventas_3m_pct) if (ma and ma.variacion_ventas_3m_pct is not None) else 0.0
        var_ventas_yoy = (
            float(ma.variacion_ventas_yoy_3m_pct)
            if (ma and getattr(ma, "variacion_ventas_yoy_3m_pct", None) is not None)
            else None
        )

        if var_ventas_yoy is not None:
            # Historia >= 15 meses: descartar ciclo estacional (e.g. estacionalidad agrícola)
            if var_ventas_3m < -40.0 and var_ventas_yoy < -20.0:
                phi -= 0.50
                castigos.append(f"Contracción crítica de ventas confirmada YoY (3M vs 12M: {var_ventas_3m:.1f}%, YoY: {var_ventas_yoy:.1f}%): -0.50")
            elif var_ventas_3m < -20.0 and var_ventas_yoy < -10.0:
                phi -= 0.25
                castigos.append(f"Contracción de ventas confirmada YoY (3M vs 12M: {var_ventas_3m:.1f}%, YoY: {var_ventas_yoy:.1f}%): -0.25")
            elif var_ventas_3m < -20.0:
                castigos.append(f"Ciclo estacional trimestral verificado y neutralizado por estabilidad interanual YoY ({var_ventas_yoy:+.1f}%)")
        else:
            if var_ventas_3m < -40.0:
                phi -= 0.50
                castigos.append("Caída crítica de ventas 3M vs 12M (>40%): -0.50")
            elif var_ventas_3m < -20.0:
                phi -= 0.25
                castigos.append("Caída significativa de ventas 3M vs 12M (>20%): -0.25")

        # 2. Mora efectiva últimos 12 meses (tomar los 12 meses más recientes)
        sorted_f29 = sorted(tax_folder.f29, key=lambda f: f.periodo or "")
        last_12_f29 = sorted_f29[-12:] if len(sorted_f29) >= 12 else sorted_f29
        mora_12m = sum(
            1 for f in last_12_f29 for d in f.detalles if d.codigo == "94" and _parse_monto(d.valor) > 0
        )
        if mora_12m > 0:
            penal_mora = min(0.60, mora_12m * 0.15)
            phi -= penal_mora
            castigos.append(f"{mora_12m} mes(es) con mora efectiva F29 en últimos 12M: -{penal_mora:.2f}")

        # 3. Postergación de IVA repetida en últimos 6 meses más recientes
        last_6_f29 = sorted_f29[-6:] if len(sorted_f29) >= 6 else sorted_f29
        posterg_6m = sum(
            1 for f in last_6_f29 for d in f.detalles if d.codigo in ("779", "755", "756") and _parse_monto(d.valor) > 0
        )
        if posterg_6m >= 2:
            phi -= 0.20
            castigos.append(f"{posterg_6m} meses con postergación IVA en últimos 6M: -0.20")

        # 4. Lagunas de declaración
        lagunas_count = len(calidad.meses_f29_faltantes)
        if lagunas_count >= 2:
            phi = 0.0
            castigos.append(f"{lagunas_count} meses sin declaración F29: Cupo anulado por omisión tributaria (0.0)")
        elif lagunas_count == 1:
            phi -= 0.40
            castigos.append("1 mes sin declaración F29: -0.40")

        phi = max(0.0, phi)
        cupo_preliminar = techo_con_flujo * phi

        # Paso D: Freno Patrimonial por CPT (12% línea limpia, hasta 20% con garantías, $0 si CPT <= 0)
        cpt = None
        f22_validos = [f for f in tax_folder.f22 if f.capital_propio_tributario is not None]
        if f22_validos:
            cpt = f22_validos[0].capital_propio_tributario

        tope_cpt = None
        aval_obligatorio = False
        cupo_excepcional = None

        if cpt is not None:
            if cpt > 0:
                requiere_garantia_conductual = (phi < 0.80) or (mora_12m > 0) or (posterg_6m >= 2)
                pct_cpt = 0.20 if requiere_garantia_conductual else 0.12
                tope_cpt = float(cpt) * pct_cpt
                cupo_ajustado = min(cupo_preliminar, tope_cpt)
                if cupo_preliminar > tope_cpt:
                    castigos.append(
                        f"Tope Patrimonial CPT ({int(pct_cpt * 100)}% de CPT: ${tope_cpt:,.0f}): "
                        f"cupo preliminar ajustado a ${cupo_ajustado:,.0f}"
                    )
            else:
                # CPT Negativo / Quiebra Técnica: Cupo directo en línea limpia es $0
                cupo_ajustado = 0.0
                aval_obligatorio = True
                cupo_excepcional = int(round(min(c_base * 0.03, 5_000_000) / 100_000.0) * 100_000)
                castigos.append(
                    f"Capital Propio Tributario Negativo (${cpt:,.0f} CLP) — Quiebra Técnica: "
                    f"Cupo directo en línea limpia rechazado ($0). "
                    f"Solo evaluable cupo excepcional garantizado de hasta ${cupo_excepcional:,.0f} CLP "
                    f"contra Pagaré Notarial y Aval Solidario con patrimonio acreditado fuera de la sociedad"
                )
        else:
            cupo_ajustado = cupo_preliminar

        # Redondeo conservador hacia abajo al centenar de M$ ($100.000 CLP)
        cupo_maximo_sugerido = _floor_m100(cupo_ajustado)

        memoria = {
            "periodo_inicio": periodo_inicio,
            "periodo_fin": periodo_fin,
            "ventas_netas_mensuales_prom": int(round(prom_ventas_12m)),
            "base_compras_c_base": int(round(c_base)),
            "spread_operacional_f29": int(round(spread_operacional_f29)),
            "brecha_operacional_proxy": int(round(spread_operacional_f29)),
            "rli_ultimo_f22": int(round(rli_val)) if rli_val is not None else None,
            "rli_mensualizada_f22": int(round(rli_mensualizada)) if rli_mensualizada is not None else None,
            "techo_operativo_8pct": int(round(techo_operativo)),
            "techo_operativo_20pct": int(round(techo_operativo)),
            "techo_operativo": int(round(techo_operativo)),
            "freno_flujo_operacional_25pct": int(round(freno_flujo)),
            "freno_absorcion_operacional": int(round(freno_flujo)),
            "margen_operacional_depurado_mensual": int(round(spread_operacional_f29)),
            "factor_riesgo_phi": round(phi, 2),
            "factor_ajuste_conductual_pct": int(round(phi * 100)),
            "cupo_preliminar": int(round(cupo_preliminar)),
            "capital_propio_tributario": cpt,
            "tope_patrimonial_12pct_cpt": int(round(tope_cpt)) if tope_cpt is not None else None,
            "tope_patrimonial_35pct_cpt": int(round(tope_cpt)) if tope_cpt is not None else None,
            "tope_patrimonial_cpt": int(round(tope_cpt)) if tope_cpt is not None else None,
            "cupo_maximo_sugerido": cupo_maximo_sugerido,
            "cupo_excepcional_garantizado": cupo_excepcional,
            "castigos_aplicados": castigos,
        }

        return cupo_maximo_sugerido, memoria, aval_obligatorio

    # ------------------------------------------------------------------
    # Indicadores
    # ------------------------------------------------------------------
    def _calcular_indicadores(
        self,
        tax_folder: TaxFolder,
        cupo_solicitado: int | None,
        cupo_maximo_sugerido: int,
    ) -> Indicadores:
        return Indicadores(
            mora_efectiva=self._mora_efectiva(tax_folder),
            margen_vs_giro=self._margen_vs_giro(tax_folder),
            respaldo_estructural=self._respaldo_estructural(
                tax_folder, cupo_solicitado, cupo_maximo_sugerido
            ),
        )

    @staticmethod
    def _mora_efectiva(tax_folder: TaxFolder) -> MoraEfectiva:
        meses_con_recargo = 0
        meses_con_remanente = 0
        for f29 in tax_folder.f29:
            for det in f29.detalles:
                if det.codigo == "94" and _parse_monto(det.valor) > 0:
                    meses_con_recargo += 1
                if det.codigo == "504" and _parse_monto(det.valor) > 0:
                    meses_con_remanente += 1

        n = len(tax_folder.f29)
        if n == 0:
            return MoraEfectiva(confianza="sin_datos")

        pct_mora = meses_con_recargo / n
        score = round(max(0, 100 - pct_mora * 100 * 4))
        confianza = "alta" if n >= 12 else "media" if n >= 6 else "baja"

        return MoraEfectiva(
            score=score,
            meses_con_recargo=meses_con_recargo,
            meses_con_remanente_credito=meses_con_remanente,
            meses_evaluados=n,
            confianza=confianza,
        )

    def _margen_vs_giro(self, tax_folder: TaxFolder) -> MargenVsGiro:
        last_12 = (
            tax_folder.monthly_taxes[-12:]
            if len(tax_folder.monthly_taxes) >= 12
            else tax_folder.monthly_taxes
        )
        debitos = [m.debito_fiscal for m in last_12 if m.debito_fiscal is not None]
        creditos_op = [
            m.credito_operacional if m.credito_operacional is not None else m.credito_fiscal
            for m in last_12
        ]
        creditos_op_validos = [c for c in creditos_op if c is not None]

        ratio = None
        ma = tax_folder.monthly_analysis
        if (
            ma is not None
            and getattr(ma, "costo_operativo_proxy_aplica", False)
            and getattr(ma, "promedio_costo_operativo_proxy_12m", None)
            and getattr(ma, "promedio_ventas_mensual", None)
        ):
            costo_proxy = float(ma.promedio_costo_operativo_proxy_12m)
            v_prom = float(ma.promedio_ventas_mensual)
            if costo_proxy > 0 and v_prom > 0:
                ratio = round(v_prom / costo_proxy, 3)
        elif debitos and creditos_op_validos and sum(creditos_op_validos) > 0:
            ratio = round(float(sum(debitos) / sum(creditos_op_validos)), 3)
        elif debitos and sum(debitos) > 0:
            ratio = 2.0

        actividad = _actividad_principal(tax_folder.activities)
        codigo_actividad = actividad.codigo if actividad else None
        descripcion = actividad.descripcion if actividad else None

        ratio_promedio, n_empresas = self.benchmark.lookup(codigo_actividad)

        score = None
        confianza = "sin_datos"

        if ratio is not None:
            if ratio_promedio and n_empresas >= 5:
                relativo = ratio / ratio_promedio
                score = round(min(100, max(0, relativo * 70)))
                confianza = "alta"
            else:
                # Evaluación autónoma de dinámica operativa intrínseca (ratio + tendencia 3M)
                if len(tax_folder.f29) >= MESES_MINIMOS_PARA_SCORING:
                    if ratio >= 1.50:
                        base = 85
                    elif ratio >= 1.30:
                        base = 75
                    elif ratio >= 1.15:
                        base = 68
                    elif ratio >= 1.00:
                        base = 58
                    elif ratio >= 0.80:
                        base = 42
                    else:
                        base = 25

                    var_3m = (
                        float(tax_folder.monthly_analysis.variacion_ventas_3m_pct)
                        if (tax_folder.monthly_analysis and tax_folder.monthly_analysis.variacion_ventas_3m_pct is not None)
                        else 0.0
                    )
                    adj = 0
                    if var_3m > 20.0:
                        adj = 10
                    elif var_3m > 5.0:
                        adj = 5
                    elif var_3m < -20.0:
                        adj = -15
                    elif var_3m < -40.0:
                        adj = -25

                    score = round(min(100, max(0, base + adj)))
                    confianza = "media"
                else:
                    confianza = "insuficiente_muestra"

        return MargenVsGiro(
            score=score,
            ratio_debito_credito_12m=ratio,
            codigo_actividad=codigo_actividad,
            descripcion_actividad=descripcion,
            ratio_promedio_sector=ratio_promedio,
            n_empresas_referencia=n_empresas,
            confianza=confianza,
        )

    @staticmethod
    def _respaldo_estructural(
        tax_folder: TaxFolder,
        cupo_solicitado: int | None,
        cupo_maximo_sugerido: int,
    ) -> RespaldoEstructural:
        f22_ordenados = sorted(
            (f for f in tax_folder.f22 if f.capital_propio_tributario is not None),
            key=lambda f: f.anio_tributario or "",
            reverse=True,
        )

        cpt = f22_ordenados[0].capital_propio_tributario if f22_ordenados else None

        # Si cupo_solicitado fue ingresado y es > 0, evaluamos contra él; si es 0 o None, evaluamos contra el cupo autónomo
        if cupo_solicitado and cupo_solicitado > 0:
            cupo_ref = cupo_solicitado
        else:
            cupo_ref = max(5_000_000, cupo_maximo_sugerido)

        veces = None
        score = None
        confianza = "sin_datos"

        if cpt is not None:
            confianza = "alta"
            if cpt > 0:
                veces = round(cpt / cupo_ref, 2)
                score = round(min(100, max(0, veces * 25)))
            else:
                veces = round(cpt / cupo_ref, 2)
                score = 15  # Castigo para CPT negativo

        return RespaldoEstructural(
            score=score,
            capital_propio_tributario=cpt,
            cupo_solicitado=cupo_solicitado,
            cupo_referencia=cupo_ref if cpt is not None else None,
            veces_cobertura=veces,
            confianza=confianza,
        )

    # ------------------------------------------------------------------
    # Desglose del Score Tributario en 6 Pilares (100 pts)
    # ------------------------------------------------------------------
    @staticmethod
    def _calcular_desglose_score(
        tax_folder: TaxFolder,
        calidad: CalidadDatos,
        hechos: Hechos,
        indicadores: Indicadores,
        memoria: dict[str, Any],
        rli_comprimida: bool,
        vigencia: dict[str, Any],
        conciliacion: dict[str, Any] | None,
    ) -> list[PilarScore]:
        pilares: list[PilarScore] = []

        # 1. Continuidad y Antigüedad Operacional (15 pts)
        n_meses = len(tax_folder.monthly_taxes) or len(tax_folder.f29)
        lagunas = len(calidad.meses_f29_faltantes)
        if n_meses >= 24 and lagunas == 0:
            p1 = 15
            det1 = f"{n_meses} meses continuos declarados sin lagunas tributarias (Historial extendido)"
        elif n_meses >= 12 and lagunas == 0:
            p1 = 13
            det1 = f"{n_meses} meses continuos declarados sin lagunas tributarias (Historial anual estándar)"
        elif n_meses >= 6 and lagunas == 0:
            p1 = 10
            det1 = f"{n_meses} meses de operación formal evaluada"
        else:
            base_m = min(10, n_meses * 2)
            penal = lagunas * 6
            p1 = max(0, base_m - penal)
            det1 = f"{n_meses} meses evaluados con {lagunas} mes(es) de omisión/laguna"
        pilares.append(PilarScore(
            nombre="Continuidad y Antigüedad Operacional",
            puntaje_obtenido=p1,
            puntaje_maximo=15,
            detalle=det1,
        ))

        # 2. Nivel y Estabilidad de Ventas F29 (20 pts)
        ma = tax_folder.monthly_analysis
        var_3m = float(ma.variacion_ventas_3m_pct) if (ma and ma.variacion_ventas_3m_pct is not None) else 0.0
        var_yoy = float(ma.variacion_ventas_yoy_3m_pct) if (ma and getattr(ma, "variacion_ventas_yoy_3m_pct", None) is not None) else None
        if var_3m >= 15.0:
            p2 = 20
            det2 = f"Crecimiento trimestral robusto (+{var_3m:.1f}%)"
        elif var_3m >= 0.0:
            p2 = 17
            det2 = f"Ventas estables con ligera expansión (+{var_3m:.1f}%)"
        elif var_3m >= -15.0:
            p2 = 14
            det2 = f"Variación prom. últ. 3M vs. promedio 12M ({var_3m:.1f}%)"
        elif var_yoy is not None and var_yoy >= -10.0:
            p2 = 14
            det2 = f"Contracción trimestral estacional ({var_3m:.1f}%) compensada por estabilidad YoY ({var_yoy:+.1f}%)"
        elif var_3m >= -30.0:
            p2 = 9
            det2 = f"Contracción de ventas moderada ({var_3m:.1f}%)"
        else:
            p2 = 4
            det2 = f"Contracción severa de ventas reciente ({var_3m:.1f}%)"
        pilares.append(PilarScore(
            nombre="Nivel y Estabilidad de Ventas F29",
            puntaje_obtenido=p2,
            puntaje_maximo=20,
            detalle=det2,
        ))

        # 3. Margen Tributario F29 Proxy (20 pts)
        ratio = indicadores.margen_vs_giro.ratio_debito_credito_12m if indicadores.margen_vs_giro else None
        if ratio is not None:
            if ratio >= 1.40:
                p3 = 20
                det3 = f"Generación neta de Débito Fiscal sólida (Ratio Débito/Crédito: {ratio:.2f}x)"
            elif ratio >= 1.20:
                p3 = 17
                det3 = f"Margen operacional suficiente (Ratio Débito/Crédito: {ratio:.2f}x)"
            elif ratio >= 1.05:
                p3 = 14
                det3 = f"Margen operacional ajustado (Ratio Débito/Crédito: {ratio:.2f}x)"
            elif ratio >= 0.95:
                p3 = 10
                det3 = f"Equilibrio fiscal neutro (Ratio Débito/Crédito: {ratio:.2f}x)"
            else:
                p3 = 5
                det3 = f"Crédito fiscal persistente sobre ventas (Ratio: {ratio:.2f}x)"
        else:
            p3 = 14
            det3 = "Margen operativo referencial estándar del giro"
        pilares.append(PilarScore(
            nombre="Margen Tributario F29 Proxy",
            puntaje_obtenido=p3,
            puntaje_maximo=20,
            detalle=det3,
        ))

        # 4. Rentabilidad (RLI) y Respaldo Patrimonial F22 (15 pts)
        cpt = memoria.get("capital_propio_tributario")
        if cpt is not None:
            if cpt <= 0:
                p4 = 0
                det4 = f"Quiebra patrimonial técnica / CPT Negativo (${cpt:,.0f} CLP)"
            else:
                cupo_ref = memoria.get("cupo_maximo_sugerido") or 5_000_000
                veces = cpt / cupo_ref if cupo_ref else 1.0
                cpt_m = round(cpt / 1000.0)
                cpt_fmt = f"{cpt_m:,}".replace(",", ".")
                ref_txt = f"Referencia Patrimonial Tributaria (CPT: M$ {cpt_fmt} — Respaldo contable no líquido)"
                if veces >= 2.0:
                    p4 = 15
                    det4 = f"{ref_txt}: Cobertura holgada"
                elif veces >= 1.0:
                    p4 = 12
                    det4 = f"{ref_txt}: Cobertura suficiente"
                else:
                    p4 = 8
                    det4 = f"{ref_txt}: Cobertura acotada"
        else:
            p4 = 8
            det4 = "Sin declaración F22 con CPT informado"

        if rli_comprimida:
            p4 = max(0, p4 - 6)
            det4 += " [Penalización -6 pts por Alerta de Compresión de RLI en último F22]"

        pilares.append(PilarScore(
            nombre="Rentabilidad (RLI) y Respaldo Patrimonial F22",
            puntaje_obtenido=p4,
            puntaje_maximo=15,
            detalle=det4,
        ))

        # 5. Cumplimiento Fiscal (Mora y Postergación IVA) (15 pts)
        mora = indicadores.mora_efectiva.meses_con_recargo if indicadores.mora_efectiva else 0
        posterg = hechos.postergaciones_iva.meses_con_postergacion if hechos and hechos.postergaciones_iva else 0
        if mora == 0 and posterg <= 1:
            p5 = 15
            det5 = "Impecable cumplimiento fiscal: 0 períodos con recargos por mora fiscal en F29 (Cód. 94) y sin postergaciones recurrentes"
        elif mora == 0 and posterg >= 2:
            p5 = 11
            det5 = f"Sin mora en F29, pero registra {posterg} meses de postergación de IVA"
        elif mora == 1:
            p5 = 8
            det5 = "Registra 1 mes con recargo/interés por mora en F29"
        elif mora == 2:
            p5 = 4
            det5 = "Registra 2 meses con recargo por mora en F29"
        else:
            p5 = 0
            det5 = f"Mora fiscal recurrente ({mora} meses con recargo Cód. 94)"
        pilares.append(PilarScore(
            nombre="Cumplimiento Fiscal (Mora y Postergación IVA)",
            puntaje_obtenido=p5,
            puntaje_maximo=15,
            detalle=det5,
        ))

        # 6. Coherencia F29/F22 y Vigencia de Información (15 pts)
        meses_desfase = vigencia.get("meses_desfase", 0) if vigencia else 0
        confianza_vig = vigencia.get("nivel_confianza", "MEDIA") if vigencia else "MEDIA"
        if meses_desfase <= 2:
            p_vig = 7
            det_vig = f"desfase {meses_desfase}m (confianza {confianza_vig})"
        elif meses_desfase <= 4:
            p_vig = 5
            det_vig = f"desfase {meses_desfase}m (confianza {confianza_vig})"
        else:
            p_vig = 2
            det_vig = f"desfase prolongado de {meses_desfase}m"

        if conciliacion:
            dif_pct = conciliacion.get("diferencia_pct", 0.0)
            if dif_pct <= 10.0:
                p_conc = 8
                det_conc = f"conciliación F29/F22 consistente ({dif_pct}% dif.)"
            elif dif_pct <= 15.0:
                p_conc = 5
                det_conc = f"conciliación F29/F22 con tolerancia ({dif_pct}% dif.)"
            else:
                p_conc = 2
                det_conc = f"desviación F29 vs F22 ({dif_pct}% dif.)"
        else:
            p_conc = 5
            det_conc = "sin cruce anual F29/F22"

        p6 = min(15, p_vig + p_conc)
        det6 = f"Vigencia: {det_vig}. Coherencia: {det_conc}"
        pilares.append(PilarScore(
            nombre="Coherencia F29/F22 y Vigencia de Información",
            puntaje_obtenido=p6,
            puntaje_maximo=15,
            detalle=det6,
        ))

        return pilares

    # ------------------------------------------------------------------
    # Composición final
    # ------------------------------------------------------------------
    @staticmethod
    def _componer_score(
        indicadores: Indicadores, desglose: list[PilarScore] | None = None
    ) -> int | None:
        scores = [
            s.score
            for s in (
                indicadores.mora_efectiva,
                indicadores.margen_vs_giro,
                indicadores.respaldo_estructural,
            )
            if s.score is not None
        ]
        if len(scores) < 2:
            return None
        if desglose:
            return sum(p.puntaje_obtenido for p in desglose)
        return round(sum(scores) / len(scores))

    @staticmethod
    def _decidir(
        hechos: Hechos,
        indicadores: Indicadores,
        score_compuesto: int | None,
        cupo_solicitado: int | None,
        cupo_maximo: int,
        memoria: dict[str, Any],
        aval_obligatorio: bool,
        tax_folder: TaxFolder | None = None,
        rli_comprimida: bool = False,
        boletin_comercial: str = "Pendiente de consulta (Condiciona línea)",
        historial_pago: str = "Cliente nuevo (Sin historial previo)",
    ) -> Decision:
        # Extraer representantes legales para resguardos personalizados (todos los registrados, sin truncar)
        rep_names = []
        if tax_folder and getattr(tax_folder, "representatives", None):
            for r in tax_folder.representatives:
                nom = getattr(r, "nombre", None) or (r.get("nombre") if isinstance(r, dict) else None)
                if nom and str(nom).strip():
                    rep_names.append(str(nom).strip())
        reps_registrados = " / ".join(rep_names) if rep_names else "No informados"

        clausula_pagare = (
            f"Pagaré a la vista suscrito ante notario por apoderado(s) con facultades suficientes según "
            f"Certificado de Vigencia y Poderes (Representantes registrados en SII: {reps_registrados})"
        )

        cpt_val = memoria.get("capital_propio_tributario")
        cpt_negativo = cpt_val is not None and cpt_val <= 0
        cupo_excepcional = memoria.get("cupo_excepcional_garantizado")

        prefix_base = "Condición base previa: Verificación de Boletín Comercial (Dicom/Equifax) sin protestos ni morosidad vigente, "

        # Desempeño Tributario SII (evalúa exclusivamente comportamiento tributario ante el SII)
        if score_compuesto is not None:
            if score_compuesto >= 85:
                desempeno_sii = "Desempeño Tributario Alto"
            elif score_compuesto >= 70:
                desempeno_sii = "Desempeño Tributario Medio"
            else:
                desempeno_sii = "Desempeño Tributario Bajo"
        else:
            desempeno_sii = "Sin Calificación"

        # Validación de mora F29 reciente y alertas
        mora_12m = indicadores.mora_efectiva.meses_con_recargo if indicadores.mora_efectiva else 0
        posterg_6m = hechos.postergaciones_iva.meses_con_postergacion if hechos and hechos.postergaciones_iva else 0
        phi_val = memoria.get("factor_riesgo_phi", 1.0)

        tiene_morosidad_comercial = "con morosidad" in boletin_comercial.lower()
        es_cliente_nuevo = "cliente nuevo" in historial_pago.lower()
        tiene_atrasos_previos = "atrasos previos" in historial_pago.lower()
        dicom_pendiente = "pendiente" in boletin_comercial.lower()

        condicion_escalamiento = (
            "Habilitable tras 2 a 3 ciclos de pago completos y oportunos, "
            "sujeta a Dicom/Equifax sin morosidad vigente, constitución de resguardo "
            "(pagaré a la vista / seguro de crédito) y validación de estados financieros."
        )

        if score_compuesto is None:
            resultado_base = "NO_EVALUABLE"
            evaluacion_referencial = "NO_EVALUABLE"
            clasificacion_riesgo = "NO_EVALUABLE"
            cupo_aprobado = 0
            linea_inicial = 0
            linea_maxima = 0
            pct_apertura = 0.0
            plazo_dias = 0
            plazo_inicial = "Contado (0 días)"
            resguardo = "Carpeta sin información suficiente para evaluar línea de crédito."
            protocolo = "Completar información tributaria faltante (mínimo 6 meses F29 y F22)."

        elif tiene_morosidad_comercial or cpt_negativo or cupo_maximo == 0 or score_compuesto < 70 or mora_12m >= 2:
            resultado_base = "RECHAZADO"
            evaluacion_referencial = "RIESGO TRIBUTARIO ALTO — Se Recomienda Operar al Contado"
            clasificacion_riesgo = "RIESGO TRIBUTARIO ALTO"
            cupo_aprobado = 0
            linea_inicial = 0
            linea_maxima = 0
            pct_apertura = 0.0
            plazo_dias = 0
            plazo_inicial = "Contado (0 días)"
            if tiene_morosidad_comercial:
                resguardo = (
                    "Bloqueo comercial por morosidad vigente en Boletín Comercial (Dicom/Equifax): "
                    "Línea de crédito no sugerida (M$ 0). Operación exclusiva al contado anticipado previo al despacho."
                )
                protocolo = "No despachar a crédito mientras existan protestos o morosidades activas en el sistema comercial."
            elif cpt_negativo:
                excep_m = (cupo_excepcional // 1000) if cupo_excepcional else 0
                resguardo = (
                    prefix_base
                    + f"línea sugerida M$ 0 por CPT negativo (${cpt_val:,.0f} CLP) — operación al contado anticipado previo al despacho. "
                    f"Únicamente evaluable cupo excepcional de hasta M$ {excep_m:,}".replace(",", ".")
                    + f" con {clausula_pagare} y Aval Solidario con patrimonio acreditado fuera de la sociedad."
                )
                protocolo = (
                    "No despachar a crédito sin resguardo notarial de avalista externo calificado. "
                    "Venta al contado con pago contra entrega."
                )
            else:
                resguardo = (
                    prefix_base
                    + "línea de crédito no sugerida M$ 0 (Venta exclusiva al contado / Pago anticipado previo al despacho)."
                )
                protocolo = "No despachar a crédito. Operación recomendada exclusivamente al contado o pago anticipado."

        elif score_compuesto >= 85:
            resultado_base = "APROBADO"
            evaluacion_referencial = "RIESGO TRIBUTARIO BAJO (Línea Condicionada a Dicom)"
            clasificacion_riesgo = "RIESGO TRIBUTARIO BAJO"
            pct_apertura = 0.50
            linea_maxima = min(cupo_solicitado, cupo_maximo) if cupo_solicitado and cupo_solicitado > 0 else cupo_maximo
            linea_maxima = _floor_m100(linea_maxima)
            linea_inicial = _floor_m100(linea_maxima * pct_apertura)
            cupo_aprobado = linea_inicial
            plazo_dias = 30
            plazo_inicial = "15 días (o 30 días con 50% de anticipo)" if (dicom_pendiente or es_cliente_nuevo) else "30 días"
            resguardo = (
                prefix_base
                + f"{clausula_pagare} o Seguro de Crédito que cubra la línea; "
                "alternativamente operar bajo esquema mixto (50% anticipo + 50% a 30 días)."
            )
            protocolo = (
                "Venta con esquema mixto (50% anticipo + 50% a 30 días contra aceptación en SII) "
                "o pagaré firmado en original ante notario según poderes vigentes antes del primer despacho."
                + (" Solicitar Balance de 8 Columnas reciente por condición suspensiva de compresión de RLI." if rli_comprimida else "")
            )

        elif score_compuesto >= 75:
            resultado_base = "APROBADO_CON_CONDICIONES"
            evaluacion_referencial = "RIESGO TRIBUTARIO MEDIO (Línea Condicionada)"
            clasificacion_riesgo = "RIESGO TRIBUTARIO MEDIO"
            pct_apertura = 0.35
            linea_maxima = min(cupo_solicitado, cupo_maximo) if cupo_solicitado and cupo_solicitado > 0 else cupo_maximo
            linea_maxima = _floor_m100(linea_maxima)
            linea_inicial = _floor_m100(linea_maxima * pct_apertura)
            cupo_aprobado = linea_inicial
            plazo_dias = 30
            plazo_inicial = "15 días (o 30 días con 50% de anticipo)"
            resguardo = (
                prefix_base
                + f"{clausula_pagare} o Seguro de Crédito que cubra la línea; "
                "alternativamente operar bajo esquema mixto (50% anticipo + 50% a 30 días)."
            )
            protocolo = (
                "Venta con esquema mixto (50% anticipo + 50% a 30 días contra aceptación en SII) "
                "o pagaré firmado en original ante notario según poderes vigentes antes del primer despacho."
                + (" Solicitar Balance de 8 Columnas reciente por condición suspensiva de compresión de RLI." if rli_comprimida else "")
            )

        else:
            # Score 65 a 74 (o 70 a 74)
            resultado_base = "APROBADO_CON_CONDICIONES"
            evaluacion_referencial = "RIESGO TRIBUTARIO MEDIO (Línea Condicionada)"
            clasificacion_riesgo = "RIESGO TRIBUTARIO MEDIO"
            pct_apertura = 0.25
            linea_maxima = min(cupo_solicitado, cupo_maximo) if cupo_solicitado and cupo_solicitado > 0 else cupo_maximo
            linea_maxima = _floor_m100(linea_maxima)
            linea_inicial = _floor_m100(linea_maxima * pct_apertura)
            cupo_aprobado = linea_inicial
            plazo_dias = 30
            plazo_inicial = "15 días (o 30 días con 50% de anticipo)"
            resguardo = (
                prefix_base
                + f"{clausula_pagare} o Seguro de Crédito que cubra la línea; "
                "alternativamente operar bajo esquema mixto (50% anticipo + 50% a 30 días)."
            )
            protocolo = (
                "Venta con esquema mixto (50% anticipo + 50% a 30 días contra aceptación en SII) "
                "o pagaré firmado en original ante notario según poderes vigentes antes del primer despacho."
                + (" Solicitar Balance de 8 Columnas reciente por condición suspensiva de compresión de RLI." if rli_comprimida else "")
            )

        caminos: list[CaminoMitigacion] = []
        alto_facturado = (hechos.composicion_ventas.pct_facturado or 0) > 0.6
        caminos.append(
            CaminoMitigacion(
                condicion="cesion_facturas_factoring",
                aplica=alto_facturado,
                resultado="APROBADO" if alto_facturado else "NO_APLICA",
                cupo_sugerido=linea_maxima if alto_facturado else None,
                justificacion=(
                    "alta proporción de ventas facturadas B2B permite ceder facturas como garantía de cobro"
                    if alto_facturado
                    else "proporción facturada insuficiente para estructurar cesión de facturas"
                ),
            )
        )

        mora_sana = (indicadores.mora_efectiva.score or 0) >= 85
        caminos.append(
            CaminoMitigacion(
                condicion="pago_contado_con_descuento",
                aplica=mora_sana,
                resultado="APROBADO" if mora_sana else "NO_APLICA",
                justificacion=(
                    "historial sin recargos por mora en declaraciones tributarias"
                    if mora_sana
                    else "historial de mora requiere operar con pago anticipado"
                ),
            )
        )

        hoja_ruta = [
            f"Clasificación y Recomendación: {evaluacion_referencial}.",
            f"Puntaje Tributario SII: {score_compuesto or '—'}/100 pts ({desempeno_sii}).",
            (
                f"Línea Inicial Recomendada (Etapa 1 - {int(round(pct_apertura * 100))}% Apertura): {format_mclp(linea_inicial)} (Plazo: {plazo_inicial})."
                if linea_inicial > 0
                else "Línea Inicial Recomendada: M$ 0 (Modalidad Contado)."
            ),
            (
                f"Línea Máxima Condicionada (Etapa 2 - Techo Técnico): {format_mclp(linea_maxima)} (Plazo: {plazo_dias} días)."
                if linea_maxima > 0
                else "Línea Máxima Condicionada: M$ 0."
            ),
            f"Resguardo comercial sugerido: {resguardo}",
            f"Condición de escalamiento: {condicion_escalamiento}",
            f"Protocolo operativo: {protocolo}",
        ]
        if alto_facturado and linea_maxima > 0:
            hoja_ruta.append("Habilitada alternativa de factoring o cesión de facturas para compras sobre la línea sugerida.")
        if cpt_negativo and cupo_excepcional:
            hoja_ruta.append(
                f"Protocolo CPT negativo: solo evaluable cupo excepcional de hasta {format_mclp(cupo_excepcional)}"
                + " con Aval Solidario calificado con patrimonio acreditado fuera de la sociedad."
            )

        memoria["linea_maxima_condicionada"] = linea_maxima
        memoria["linea_inicial_sugerida"] = linea_inicial
        memoria["plazo_inicial_sugerido"] = plazo_inicial
        memoria["pct_apertura_inicial"] = int(round(pct_apertura * 100))
        memoria["condicion_escalamiento"] = condicion_escalamiento
        memoria["boletin_comercial"] = boletin_comercial
        memoria["historial_pago"] = historial_pago

        return Decision(
            resultado_base=resultado_base,
            evaluacion_referencial=evaluacion_referencial,
            clasificacion_riesgo=clasificacion_riesgo,
            desempeno_tributario_texto=desempeno_sii,
            producto_evaluado="credito_30_dias",
            cupo_maximo_sugerido=linea_maxima,
            cupo_aprobado=linea_inicial,
            linea_maxima_sugerida=linea_maxima,
            linea_inicial_sugerida=linea_inicial,
            linea_maxima_condicionada=linea_maxima,
            plazo_sugerido_dias=plazo_dias,
            plazo_inicial_sugerido=plazo_inicial,
            condicion_escalamiento=condicion_escalamiento,
            garantia_exigida=resguardo,
            resguardo_comercial_sugerido=resguardo,
            protocolo_operativo=protocolo,
            memoria_calculo=memoria,
            hoja_ruta_comercial=hoja_ruta,
            caminos_mitigacion=caminos,
            variables_comerciales={
                "boletin_comercial": boletin_comercial,
                "historial_pago": historial_pago,
            },
        )

    @staticmethod
    def _alertas_y_fortalezas(
        hechos: Hechos,
        indicadores: Indicadores,
        memoria: dict[str, Any],
        calidad: CalidadDatos,
    ) -> tuple[list[str], list[str], list[str]]:
        alertas: list[str] = []
        fortalezas: list[str] = []
        banderas_rojas: list[str] = []

        # Mora
        if indicadores.mora_efectiva.meses_con_recargo > 0:
            msg = f"{indicadores.mora_efectiva.meses_con_recargo} mes(es) con recargo/interés por mora en F29"
            alertas.append(msg)
            if indicadores.mora_efectiva.meses_con_recargo >= 2:
                banderas_rojas.append(msg)
        elif indicadores.mora_efectiva.meses_evaluados > 0:
            fortalezas.append(
                f"Cero meses con mora efectiva en {indicadores.mora_efectiva.meses_evaluados} meses evaluados"
            )

        # CPT y Patrimonio
        cpt = memoria.get("capital_propio_tributario")
        if cpt is not None:
            if cpt < 0:
                msg = f"Capital Propio Tributario NEGATIVO (${cpt:,.0f} CLP) — Quiebra o pérdida patrimonial técnica"
                alertas.append(msg)
                banderas_rojas.append(msg)
            elif memoria.get("tope_patrimonial_35pct_cpt"):
                fortalezas.append(
                    f"Respaldo patrimonial sólido: CPT positivo de ${cpt:,.0f} CLP"
                )

        # Lagunas tributarias
        if calidad.meses_f29_faltantes:
            msg = f"Lagunas de declaración: {len(calidad.meses_f29_faltantes)} período(s) sin F29 en la carpeta"
            alertas.append(msg)
            if len(calidad.meses_f29_faltantes) >= 2:
                banderas_rojas.append(msg)

        # Castigos de memoria de cálculo
        for c in memoria.get("castigos_aplicados", []):
            alertas.append(c)

        return alertas, fortalezas, banderas_rojas

    @staticmethod
    def _generar_dictamen_ejecutivo(
        tax_folder: TaxFolder,
        score: int | None,
        decision: Decision,
        memoria: dict[str, Any],
        banderas_rojas: list[str],
    ) -> str:
        razon = (
            tax_folder.contributor.razon_social
            if tax_folder.contributor and tax_folder.contributor.razon_social
            else "Contribuyente"
        )
        rut = (
            tax_folder.contributor.rut
            if tax_folder.contributor and tax_folder.contributor.rut
            else "—"
        )

        lines = [
            "CAVILARIA SpA — Informe de Evaluación Tributaria y Recomendación de Línea Comercial",
            f"Contribuyente: {razon} (RUT: {rut})",
            "",
            f"Clasificación y Recomendación: {decision.evaluacion_referencial}",
            f"Puntaje Tributario SII: {score or '—'}/100 pts ({decision.desempeno_tributario_texto or 'Desempeño Tributario'})",
            f"Línea Inicial Recomendada (Etapa 1 - Apertura): {format_mclp(decision.linea_inicial_sugerida)} | Plazo Inicial: {decision.plazo_inicial_sugerido}",
            f"Línea Máxima Condicionada (Etapa 2 - Techo Técnico): {format_mclp(decision.linea_maxima_condicionada)} | Plazo Máximo: {decision.plazo_sugerido_dias} días",
            f"Resguardo Comercial Sugerido: {decision.resguardo_comercial_sugerido}",
            f"Condición de Escalamiento: {decision.condicion_escalamiento}",
            "",
            "1. Memoria Cuantitativa de Asignación:",
            f"- Base Mensual de Absorción (C_base): {format_mclp(memoria.get('base_compras_c_base', 0))}",
            f"- Techo Operativo Proveedor (8%): {format_mclp(memoria.get('techo_operativo_8pct', 0))}",
            f"- Margen Tributario F29 Proxy [Ventas - Compras - IVA]: {format_mclp(memoria.get('brecha_operacional_proxy', 0))}",
            f"- Freno Flujo Operacional (25%): {format_mclp(memoria.get('freno_flujo_operacional_25pct', 0))}",
            f"- Factor de Ajuste Conductual: {int(round(memoria.get('factor_riesgo_phi', 1.0) * 100))}%",
            f"- Capital Propio Tributario (CPT): {format_mclp(memoria.get('capital_propio_tributario'))}",
            f"- Línea Máxima Condicionada (Techo Técnico): {format_mclp(decision.linea_maxima_condicionada)}",
            f"- Línea Inicial Recomendada (Etapa 1 - 50% Apertura): {format_mclp(decision.linea_inicial_sugerida)}",
        ]
        if memoria.get("castigos_aplicados"):
            lines.append("- Ajustes de Riesgo Aplicados:")
            for ca in memoria["castigos_aplicados"]:
                lines.append(f"  * {ca}")

        if banderas_rojas:
            lines.append("")
            lines.append("2. Condiciones Suspensivas y Banderas Rojas:")
            for b in banderas_rojas:
                lines.append(f"- 🔴 {b}")

        lines.append("")
        lines.append("3. Recomendaciones Operativas:")
        for h in decision.hoja_ruta_comercial:
            lines.append(f"- ✅ {h}")

        return "\n".join(lines)


def _actividad_principal(activities: list) -> Activity | None:
    for a in activities:
        if isinstance(a, Activity) and a.principal:
            return a
    for a in activities:
        if isinstance(a, Activity):
            return a
    return None


def _parse_monto(valor: str | None) -> int:
    if not valor:
        return 0
    limpio = valor.strip().replace(".", "").replace(",", "")
    if not limpio or limpio == "-":
        return 0
    try:
        return int(limpio)
    except ValueError:
        return 0
