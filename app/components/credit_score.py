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
    st.subheader("Comité de Crédito B2B v2.0 — Asignación de Cupo Comercial")

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

    # --- PANEL EJECUTIVO DE COMITÉ ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        score_val = getattr(cr, "score_crediticio", 0.0)
        cat_val = getattr(cr, "categoria_riesgo", "MEDIO")
        st.metric("Score Crediticio", f"{score_val:.1f}/100", cat_val)
    with c2:
        veredicto_val = getattr(cr, "veredicto", "OBSERVADO")
        _show_veredicto_badge(veredicto_val)
    with c3:
        cupo_ap = getattr(cr, "cupo_aprobado", None)
        cupo_str = format_mclp(cupo_ap) if cupo_ap is not None else "—"
        st.metric("Cupo Aprobado", cupo_str)
    with c4:
        plazo = getattr(cr, "plazo_sugerido_dias", None)
        plazo_str = f"{plazo} días" if plazo else "Contado"
        garantia = getattr(cr, "garantia_exigida", None) or "Sin garantía"
        st.metric("Plazo Sugerido", plazo_str, garantia)

    st.caption("ℹ️ Cifras expresadas en Miles de Pesos Chilenos (M$)")

    dictamen = getattr(cr, "dictamen_ejecutivo", None)
    if dictamen:
        if "RECHAZADO" in str(veredicto_val):
            st.error(f"**Dictamen de Comité:** {dictamen}")
        elif "APROBADO" in str(veredicto_val) and "CONDICIONES" not in str(veredicto_val):
            st.success(f"**Dictamen de Comité:** {dictamen}")
        else:
            st.warning(f"**Dictamen de Comité:** {dictamen}")

    # --- MEMORIA DE CÁLCULO CUANTITATIVA ---
    memoria = getattr(cr, "memoria_calculo", None)
    if memoria and isinstance(memoria, dict):
        with st.expander("📊 Memoria de Cálculo Cuantitativa de Cupo (M$)", expanded=True):
            mc_c1, mc_c2, mc_c3, mc_c4 = st.columns(4)
            with mc_c1:
                st.caption("Paso A: Base Compras (C_base)")
                base_c = memoria.get("base_compras_c_base") or memoria.get("base_compras_mensual_operacional", 0)
                st.markdown(f"**{format_mclp(base_c)}**")
            with mc_c2:
                st.caption("Paso B: Techo Operativo (8%)")
                techo_op = memoria.get("techo_operativo_8pct") or memoria.get("techo_operativo", 0)
                st.markdown(f"**{format_mclp(techo_op)}**")
            with mc_c3:
                st.caption("Freno Flujo Neto (25%)")
                freno_flujo = memoria.get("freno_flujo_operacional_25pct", 0)
                st.markdown(f"**{format_mclp(freno_flujo)}**")
            with mc_c4:
                st.caption("Paso C: Calidad Riesgo (Φ)")
                phi_v = memoria.get("factor_riesgo_phi") or memoria.get("factor_phi_calidad_crediticia", 1.0)
                st.markdown(f"**{phi_v:.2f}**")

            mc_c5, mc_c6, mc_c7, mc_c8 = st.columns(4)
            with mc_c5:
                st.caption("Cupo Preliminar")
                cupo_pre = memoria.get("cupo_preliminar", 0)
                st.markdown(f"**{format_mclp(cupo_pre)}**")
            with mc_c6:
                st.caption("Capital Propio Tributario")
                cpt_v = memoria.get("capital_propio_tributario")
                st.markdown(f"**{format_mclp(cpt_v)}**" if cpt_v is not None else "**N/A**")
            with mc_c7:
                st.caption("Paso D: Tope CPT (12%/20%)")
                tope_c = memoria.get("tope_patrimonial_cpt") or memoria.get("tope_patrimonial_12pct_cpt") or memoria.get("tope_patrimonial_35pct_cpt")
                st.markdown(f"**{format_mclp(tope_c)}**" if tope_c is not None else "**Sin límite**")
            with mc_c8:
                st.caption("Cupo Máximo Sugerido")
                cupo_max = memoria.get("cupo_maximo_sugerido", 0)
                st.markdown(f"**{format_mclp(cupo_max)}**")

            st.caption("ℹ️ Cifras expresadas en Miles de Pesos Chilenos (M$)")

    # --- COMPARATIVA OPERACIONAL 12M vs 3M ---
    ma = getattr(tax_folder, "monthly_analysis", None)
    if ma:
        tc_ventas = getattr(ma, "tasa_crecimiento_ventas_trimestral", None)
        tc_compras = getattr(ma, "tasa_crecimiento_compras_trimestral", None)
        m_op = getattr(ma, "margen_operacional_implicito_promedio", None)

        # Fallback defensivo a campos legacy si los campos no estaban precalculados
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
        st.markdown("#### Banderas Rojas")
        for b in banderas:
            st.markdown(f"- 🔴 {b}")

    hoja_ruta = getattr(cr, "hoja_ruta_comercial", [])
    if hoja_ruta:
        st.markdown("#### Hoja de Ruta Comercial")
        for r in hoja_ruta:
            st.markdown(f"- 🧭 {r}")

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
    colores = {
        "APROBADO": "green",
        "APROBADO_CON_CONDICIONES": "orange",
        "RECHAZADO": "red",
        "OBSERVADO": "orange",
        "NO_EVALUABLE": "gray",
    }
    color = colores.get(str(resultado), "gray")
    st.markdown(f"### :{color}[**{str(resultado).replace('_', ' ')}**]")


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
