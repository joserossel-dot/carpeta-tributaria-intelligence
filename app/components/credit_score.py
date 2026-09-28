import streamlit as st

from app.utils.formatting import fmt_currency, format_mclp
from src.models.tax_folder import TaxFolder

_CONFIANZA_LABEL = {
    "alta": "🟢 confianza alta",
    "media": "🟡 confianza media",
    "baja": "🟠 confianza baja",
    "insuficiente_muestra": "⚪ muestra insuficiente todavía",
    "sin_datos": "⚪ sin datos suficientes",
}


def show_credit_score(tax_folder: TaxFolder) -> None:
    st.subheader("CAVILARIA SpA — Informe de Evaluación Tributaria y Recomendación de Línea Comercial")

    cr = getattr(tax_folder, "credit_risk", None)
    if cr is None:
        st.warning("El motor de riesgo crediticio no pudo evaluarse para esta carpeta.")
        return

    calidad = getattr(cr, "calidad_datos", None)
    if calidad:
        _show_calidad_datos(calidad)
        if getattr(calidad, "veredicto", None) != "APTO_PARA_SCORING":
            st.info(
                "No hay datos suficientes para calcular un score. Se necesitan al "
                "menos 6 meses de F29 y datos del contribuyente."
            )
            return

    st.divider()

    # --- PANEL EJECUTIVO DE EVALUACIÓN REFERENCIAL ---
    score_val = getattr(cr, "score_crediticio", 0.0)
    clasif_riesgo = getattr(cr, "clasificacion_riesgo", None) or getattr(cr, "categoria_riesgo", "MODERADO")
    desempeno_texto = getattr(cr, "desempeno_tributario_texto", None) or ("Desempeño Tributario Alto" if score_val >= 80 else "Desempeño Tributario Medio")
    linea_ini = getattr(cr, "linea_inicial_sugerida", None)
    linea_max = getattr(cr, "linea_maxima_condicionada", None) or getattr(cr, "cupo_maximo_sugerido", 0)
    plazo_dias = getattr(cr, "plazo_sugerido_dias", 0)
    plazo_ini = getattr(cr, "plazo_inicial_sugerido", None) or (f"{plazo_dias} días" if plazo_dias > 0 else "Contado")
    resguardo = getattr(cr, "resguardo_comercial_sugerido", None) or getattr(cr, "garantia_exigida", None) or "Sin garantía"
    eval_val = getattr(cr, "evaluacion_referencial", None) or getattr(cr, "veredicto", "OBSERVADO")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Puntaje Tributario SII", f"{score_val:.0f}/100 pts", desempeno_texto)
    with c2:
        _show_veredicto_badge(eval_val)
    with c3:
        ini_str = format_mclp(linea_ini) if linea_ini is not None else "—"
        max_str = format_mclp(linea_max) if linea_max is not None else "—"
        st.metric("Línea Inicial (Apertura)", ini_str, f"Máxima: {max_str}")
    with c4:
        st.metric("Plazo Inicial", plazo_ini, f"Máximo: {plazo_dias} días" if plazo_dias > 0 else "Contado")

    st.caption("ℹ️ Cifras expresadas en Miles de Pesos Chilenos (M$). El Puntaje Tributario evalúa comportamiento ante el SII y no reemplaza el informe comercial externo.")

    dictamen = getattr(cr, "dictamen_ejecutivo", None)
    if dictamen:
        if "ALTO" in str(eval_val) or "RECHAZADO" in str(eval_val):
            st.error(f"**Recomendación Referencial:**\n\n{dictamen}")
        elif "BAJO" in str(eval_val) or ("APROBADO" in str(eval_val) and "CONDICIONES" not in str(eval_val)):
            st.success(f"**Recomendación Referencial:**\n\n{dictamen}")
        else:
            st.warning(f"**Recomendación Referencial:**\n\n{dictamen}")

    # --- FILTRO DE ELEGIBILIDAD TRIBUTARIA (ETAPA 1) ---
    filtro = getattr(cr, "filtro_elegibilidad", [])
    if filtro:
        with st.expander("📋 Etapa 1: Filtro de Elegibilidad Tributaria", expanded=True):
            f_cols = st.columns(len(filtro))
            for i, item in enumerate(filtro):
                with f_cols[i]:
                    st_val = item.get("estado", "OBSERVADO")
                    icon = "✅" if st_val == "CUMPLE" else "⚠️"
                    st.markdown(f"**{icon} {item.get('parametro')}**")
                    st.caption(item.get("detalle"))

    # --- MEMORIA DE CÁLCULO CUANTITATIVA ---
    memoria = getattr(cr, "memoria_calculo", None)
    if memoria and isinstance(memoria, dict):
        with st.expander("📊 Memoria de Cálculo Cuantitativa de Línea (M$)", expanded=True):
            mc_c1, mc_c2, mc_c3, mc_c4 = st.columns(4)
            with mc_c1:
                st.caption("Paso A: Base Compras (C_base)")
                base_c = memoria.get("base_compras_c_base") or memoria.get("base_compras_mensual_operacional", 0)
                st.markdown(f"**{format_mclp(base_c)}**")
            with mc_c2:
                st.caption("Paso B1: Techo Operativo (8%)")
                techo_op = memoria.get("techo_operativo_8pct") or memoria.get("techo_operativo", 0)
                st.markdown(f"**{format_mclp(techo_op)}**")
            with mc_c3:
                st.caption("Spread Operacional F29")
                spread = memoria.get("spread_operacional_f29") or memoria.get("brecha_operacional_proxy", 0)
                st.markdown(f"**{format_mclp(spread)}**")
            with mc_c4:
                st.caption("Paso B2: Freno Absorción")
                freno_abs = memoria.get("freno_absorcion_operacional") or memoria.get("freno_flujo_operacional_25pct", 0)
                st.markdown(f"**{format_mclp(freno_abs)}**")

            mc_c5, mc_c6, mc_c7, mc_c8 = st.columns(4)
            with mc_c5:
                st.caption("Paso C: Ajuste Conductual")
                phi_v = memoria.get("factor_riesgo_phi") or memoria.get("factor_phi_calidad_crediticia", 1.0)
                st.markdown(f"**{int(round(phi_v * 100))}%**")
            with mc_c6:
                st.caption("Paso D: Capital Propio (CPT)")
                cpt_v = memoria.get("capital_propio_tributario")
                st.markdown(f"**{format_mclp(cpt_v)}**" if cpt_v is not None else "**N/A**")
            with mc_c7:
                st.caption("Línea Máxima Condicionada")
                cupo_max = memoria.get("linea_maxima_condicionada") or memoria.get("cupo_maximo_sugerido", 0)
                st.markdown(f"**{format_mclp(cupo_max)}**")
            with mc_c8:
                pct_ap_val = memoria.get("pct_apertura_inicial", 50)
                st.caption(f"Línea Inicial ({pct_ap_val}% Apertura)")
                cupo_ini = memoria.get("linea_inicial_sugerida") or linea_ini
                st.markdown(f"**{format_mclp(cupo_ini)}**")

            st.caption("ℹ️ Cifras expresadas en Miles de Pesos Chilenos (M$). Spread Operacional Tributario F29 = Ventas Netas - Compras Op. Netas.")

    # --- CONDICIONES SUSPENSIVAS Y MONITOREO ---
    vars_com = getattr(cr, "variables_comerciales", {}) or {}
    boletin_com = vars_com.get("boletin_comercial", "Pendiente de consulta (Condiciona línea)")
    hist_pago = vars_com.get("historial_pago", "Cliente nuevo (Sin historial previo)")
    cond_escalamiento = getattr(cr, "condicion_escalamiento", None)

    with st.expander("🛡️ Condiciones Suspensivas, Alertas y Monitoreo Sugerido", expanded=True):
        cs_c1, cs_c2 = st.columns(2)
        with cs_c1:
            st.markdown("##### Variables Comerciales Externas")
            st.markdown(f"- 🏦 **Boletín Comercial (Dicom/Equifax):** {boletin_com}")
            st.markdown(f"- 🤝 **Historial con Proveedor:** {hist_pago}")
            st.markdown(f"- 📄 **Resguardo Exigido:** {resguardo}")
        with cs_c2:
            st.markdown("##### Escalamiento y Monitoreo")
            if cond_escalamiento:
                st.markdown(f"- 🚀 **Condición de Escalamiento:** {cond_escalamiento}")
            st.markdown("- 🔍 **Monitoreo Primeros 90 Días:** Revisión mensual de pagos y vigencia de declaraciones F29.")

    # --- COMPARATIVA OPERACIONAL 12M vs 3M ---
    ma = getattr(tax_folder, "monthly_analysis", None)
    if ma:
        tc_ventas = getattr(ma, "tasa_crecimiento_ventas_trimestral", None)
        tc_compras = getattr(ma, "tasa_crecimiento_compras_trimestral", None)
        m_op = getattr(ma, "margen_operacional_implicito_promedio", None)

        if tc_ventas is None and getattr(ma, "variacion_ventas_3m_pct", None) is not None:
            try:
                tc_ventas = float(ma.variacion_ventas_3m_pct) / 100.0
            except (ValueError, TypeError):
                tc_ventas = None

        if m_op is None and getattr(ma, "margen_implicito_12m", None) is not None:
            try:
                m_op = float(ma.margen_implicito_12m)
            except (ValueError, TypeError):
                m_op = None

        if tc_ventas is not None or m_op is not None or tc_compras is not None:
            with st.expander("📈 Dinámica Operacional Reciente (12M vs 3M)", expanded=False):
                op_c1, op_c2, op_c3 = st.columns(3)
                with op_c1:
                    tc_str = f"{tc_ventas:+.1%}" if tc_ventas is not None else "N/A"
                    st.metric("Tendencia Ventas (3M vs 12M)", tc_str)
                with op_c2:
                    tcc_str = f"{tc_compras:+.1%}" if tc_compras is not None else "N/A"
                    st.metric("Tendencia Compras (3M vs 12M)", tcc_str)
                with op_c3:
                    m12_str = f"{m_op:.1%}" if m_op is not None else "N/A"
                    st.metric("Margen Implícito Operacional (12M)", m12_str)

    # --- BANDERAS ROJAS Y HOJA DE RUTA ---
    banderas = getattr(cr, "banderas_rojas", [])
    if banderas:
        st.markdown("#### Banderas Rojas y Condiciones Suspensivas")
        for b in banderas:
            st.markdown(f"- 🔴 {b}")

    hoja_ruta = getattr(cr, "hoja_ruta_comercial", [])
    if hoja_ruta:
        st.markdown("#### Hoja de Ruta Comercial")
        for r in hoja_ruta:
            st.markdown(f"- 🧭 {r}")

    # --- CONTROL DE VIGENCIA Y CONCILIACIÓN CRUZADA ---
    vigencia = getattr(cr, "vigencia_datos", None)
    conciliacion = getattr(cr, "conciliacion_f29_f22", None)
    if vigencia or conciliacion:
        st.divider()
        if vigencia:
            v_col1, v_col2 = st.columns(2)
            with v_col1:
                st.markdown(f"📅 **Emisión:** {vigencia.get('fecha_emision')} | **Último F29:** {vigencia.get('ultimo_periodo')}")
            with v_col2:
                st.markdown(f"⏱️ **Antigüedad del dato:** {vigencia.get('meses_desfase')} meses (Confianza: **{vigencia.get('nivel_confianza')}**)")
        if conciliacion:
            st.info(f"📊 **Conciliación Cruzada F29 vs F22:** {conciliacion.get('detalle')}")

    # --- DESGLOSE DEL SCORE TRIBUTARIO (6 PILARES) ---
    desglose = getattr(cr, "desglose_score", [])
    if desglose:
        st.divider()
        st.markdown("#### Desglose del Puntaje Tributario SII (6 Dimensiones — 100 Puntos)")
        for p in desglose:
            col1, col2 = st.columns([1, 3])
            with col1:
                st.metric(p.nombre, f"{p.puntaje_obtenido}/{p.puntaje_maximo} pts")
            with col2:
                st.markdown(f"**Detalle:** {p.detalle}")

    st.divider()
    st.markdown("#### Hechos Factuales")
    st.caption("Extracciones no calificadas de la carpeta tributaria.")
    hechos = getattr(cr, "hechos", None)
    if hechos:
        _show_hechos(hechos)

    st.divider()
    st.markdown("#### Pilares Cuantitativos de Riesgo")
    indicadores = getattr(cr, "indicadores", None)
    if indicadores:
        _show_indicador("Mora efectiva", getattr(indicadores, "mora_efectiva", None))
        _show_indicador("Margen vs. giro", getattr(indicadores, "margen_vs_giro", None))
        _show_indicador("Respaldo estructural", getattr(indicadores, "respaldo_estructural", None))

    decision = getattr(cr, "decision", None)
    caminos = getattr(decision, "caminos_mitigacion", []) if decision else []
    if caminos:
        st.divider()
        st.markdown("#### Caminos de mitigación")
        for camino in caminos:
            aplica = getattr(camino, "aplica", False)
            icon = "✅" if aplica else "⬜"
            condicion = getattr(camino, "condicion", "condicion").replace("_", " ").title()
            with st.expander(f"{icon} {condicion}", expanded=aplica):
                st.markdown(f"**Resultado:** {getattr(camino, 'resultado', '')}")
                cupo_sug = getattr(camino, "cupo_sugerido", None)
                if cupo_sug:
                    st.markdown(f"**Cupo sugerido:** {fmt_currency(cupo_sug)}")
                st.markdown(getattr(camino, "justificacion", ""))

    fortalezas = getattr(cr, "fortalezas", [])
    if fortalezas:
        st.divider()
        st.markdown("#### Fortalezas")
        for f in fortalezas:
            st.markdown(f"✅ {f}")

    alertas = getattr(cr, "alertas", [])
    if alertas:
        st.markdown("#### Alertas")
        for a in alertas:
            st.markdown(f"⚠️ {a}")


def _show_calidad_datos(calidad) -> None:
    veredicto = getattr(calidad, "veredicto", "NO_EVALUABLE")
    completitud = getattr(calidad, "completitud_pct", 0)
    apto = veredicto == "APTO_PARA_SCORING"
    icon = "✅" if apto else "🚫"
    st.markdown(f"{icon} **Calidad de datos:** {veredicto} ({completitud}% completo)")
    campos_no = getattr(calidad, "campos_no_confiables", [])
    if campos_no:
        with st.expander(f"{len(campos_no)} campo(s) no confiable(s)"):
            for c in campos_no:
                st.markdown(f"- **{getattr(c, 'campo', '')}**: {getattr(c, 'motivo', '')}")


def _show_veredicto_badge(resultado: str) -> None:
    res = str(resultado)
    if "BAJO" in res or ("APROBADO" in res and "CONDICIONES" not in res):
        color = "green"
    elif "MEDIO-ALTO" in res:
        color = "orange"
    elif "MEDIO" in res or "CONDICIONES" in res or "OBSERVADO" in res:
        color = "orange"
    elif "ALTO" in res or "RECHAZADO" in res:
        color = "red"
    else:
        color = "gray"
    st.markdown(f"### :{color}[**{res.replace('_', ' ')}**]")


def _show_resultado_badge(resultado: str) -> None:
    colores = {
        "APROBADO": "green",
        "APROBADO_CON_CONDICIONES": "orange",
        "RECHAZADO": "red",
        "NO_EVALUABLE": "gray",
    }
    color = colores.get(str(resultado), "gray")
    st.markdown(f":{color}[**{str(resultado).replace('_', ' ')}**] — crédito a 30 días")


def _show_hechos(hechos) -> None:
    cv = getattr(hechos, "composicion_ventas", None)
    piva = getattr(hechos, "postergaciones_iva", None)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Composición de ventas**")
        if cv and getattr(cv, "pct_facturado", None) is not None:
            pct_fact = getattr(cv, "pct_facturado", 0.0)
            pct_bol = getattr(cv, "pct_boletas", 0.0)
            meses_ev = getattr(cv, "meses_evaluados", 0)
            st.markdown(f"- {pct_fact:.0%} facturado / {pct_bol:.0%} boleta")
            st.markdown(f"- {meses_ev} meses evaluados")
        else:
            st.markdown("- Sin datos de facturación en el período evaluado")
        if cv and getattr(cv, "nota", None):
            st.caption(cv.nota)
    with col2:
        st.markdown("**Postergaciones de IVA**")
        if piva:
            m_post = getattr(piva, "meses_con_postergacion", 0)
            m_tot = getattr(piva, "total_meses_evaluados", 0)
            st.markdown(f"- {m_post} de {m_tot} meses con postergación declarada")
            periodos = getattr(piva, "periodos", [])
            if periodos:
                st.caption(f"Períodos: {', '.join(periodos)}")


def _show_indicador(titulo: str, indicador) -> None:
    if indicador is None:
        return
    col1, col2 = st.columns([1, 3])
    score = getattr(indicador, "score", None)
    confianza = getattr(indicador, "confianza", "sin_datos")
    criterio = getattr(indicador, "criterio", "")
    with col1:
        st.metric(titulo, f"{score}/100" if score is not None else "—")
    with col2:
        st.markdown(_CONFIANZA_LABEL.get(confianza, confianza))
        if criterio:
            st.caption(criterio)
