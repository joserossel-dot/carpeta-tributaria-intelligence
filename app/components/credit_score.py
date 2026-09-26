import streamlit as st

from app.utils.formatting import fmt_currency
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

    cr = tax_folder.credit_risk
    if cr is None:
        st.warning("El motor de riesgo crediticio no pudo evaluarse para esta carpeta.")
        return

    _show_calidad_datos(cr.calidad_datos)

    if cr.calidad_datos.veredicto != "APTO_PARA_SCORING":
        st.info(
            "No hay datos suficientes para calcular un score. Se necesitan al "
            "menos 6 meses de F29 y datos del contribuyente."
        )
        return

    st.divider()

    # --- PANEL EJECUTIVO DE COMITÉ ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Score Crediticio", f"{cr.score_crediticio:.1f}/100", cr.categoria_riesgo)
    with c2:
        _show_veredicto_badge(cr.veredicto)
    with c3:
        cupo_str = fmt_currency(cr.cupo_aprobado) if cr.cupo_aprobado is not None else "—"
        st.metric("Cupo Aprobado", cupo_str)
    with c4:
        plazo_str = f"{cr.plazo_sugerido_dias} días" if cr.plazo_sugerido_dias else "Contado"
        st.metric("Plazo Sugerido", plazo_str, cr.garantia_exigida or "Sin garantía")

    if cr.dictamen_ejecutivo:
        if "RECHAZADO" in cr.veredicto:
            st.error(f"**Dictamen de Comité:** {cr.dictamen_ejecutivo}")
        elif "APROBADO" in cr.veredicto and "CONDICIONES" not in cr.veredicto:
            st.success(f"**Dictamen de Comité:** {cr.dictamen_ejecutivo}")
        else:
            st.warning(f"**Dictamen de Comité:** {cr.dictamen_ejecutivo}")

    # --- MEMORIA DE CÁLCULO CUANTITATIVA ---
    if cr.memoria_calculo:
        with st.expander("📊 Memoria de Cálculo Cuantitativa de Cupo", expanded=True):
            mc = cr.memoria_calculo
            mc_c1, mc_c2, mc_c3, mc_c4 = st.columns(4)
            with mc_c1:
                st.caption("Paso A: Base Compras (30d)")
                st.markdown(f"**${mc.get('base_compras_mensual_operacional', 0):,.0f}**".replace(",", "."))
            with mc_c2:
                st.caption("Paso B: Techo Ventas (20%)")
                st.markdown(f"**${mc.get('techo_20pct_ventas_promedio', 0):,.0f}**".replace(",", "."))
            with mc_c3:
                st.caption("Paso C: Calidad Crediticia (Φ)")
                st.markdown(f"**{mc.get('factor_phi_calidad_crediticia', 0.0):.2f}**")
            with mc_c4:
                st.caption("Paso D: Freno CPT")
                freno = mc.get("cpt_freno_aplicado")
                cpt_max = mc.get("cpt_maximo_cupo")
                cpt_str = f"${cpt_max:,.0f}".replace(",", ".") if cpt_max else "N/A"
                st.markdown(f"**{'SÍ (' + cpt_str + ')' if freno else 'NO'}**")

    # --- COMPARATIVA OPERACIONAL 12M vs 3M ---
    ma = tax_folder.monthly_analysis
    if ma and (ma.tasa_crecimiento_ventas_trimestral is not None or ma.margen_operacional_implicito_promedio is not None):
        with st.expander("📈 Dinámica Operacional Reciente (12M vs 3M)", expanded=False):
            op_c1, op_c2, op_c3 = st.columns(3)
            with op_c1:
                tc = ma.tasa_crecimiento_ventas_trimestral
                tc_str = f"{tc:+.1%}" if tc is not None else "N/A"
                st.metric("Tendencia Ventas (3M vs 12M)", tc_str)
            with op_c2:
                tcc = ma.tasa_crecimiento_compras_trimestral
                tcc_str = f"{tcc:+.1%}" if tcc is not None else "N/A"
                st.metric("Tendencia Compras (3M vs 12M)", tcc_str)
            with op_c3:
                m12 = ma.margen_operacional_implicito_promedio
                m12_str = f"{m12:.1%}" if m12 is not None else "N/A"
                st.metric("Margen Implícito Operacional (12M)", m12_str)

    # --- BANDERAS ROJAS Y HOJA DE RUTA ---
    if cr.banderas_rojas:
        st.markdown("#### Banderas Rojas")
        for b in cr.banderas_rojas:
            st.markdown(f"- 🔴 {b}")

    if cr.hoja_ruta_comercial:
        st.markdown("#### Hoja de Ruta Comercial")
        for r in cr.hoja_ruta_comercial:
            st.markdown(f"- 🧭 {r}")

    st.divider()
    st.markdown("#### Hechos Factuales")
    st.caption("Extracciones no calificadas de la carpeta tributaria.")
    _show_hechos(cr.hechos)

    st.divider()
    st.markdown("#### Pilares Cuantitativos de Riesgo")
    _show_indicador("Mora efectiva", cr.indicadores.mora_efectiva)
    _show_indicador("Margen vs. giro", cr.indicadores.margen_vs_giro)
    _show_indicador("Respaldo estructural", cr.indicadores.respaldo_estructural)

    if cr.decision.caminos_mitigacion:
        st.divider()
        st.markdown("#### Caminos de mitigación")
        for camino in cr.decision.caminos_mitigacion:
            icon = "✅" if camino.aplica else "⬜"
            with st.expander(f"{icon} {camino.condicion.replace('_', ' ').title()}", expanded=camino.aplica):
                st.markdown(f"**Resultado:** {camino.resultado}")
                if camino.cupo_sugerido:
                    st.markdown(f"**Cupo sugerido:** {fmt_currency(camino.cupo_sugerido)}")
                st.markdown(camino.justificacion)

    if cr.fortalezas:
        st.divider()
        st.markdown("#### Fortalezas")
        for f in cr.fortalezas:
            st.markdown(f"✅ {f}")

    if cr.alertas:
        st.markdown("#### Alertas")
        for a in cr.alertas:
            st.markdown(f"⚠️ {a}")


def _show_calidad_datos(calidad) -> None:
    apto = calidad.veredicto == "APTO_PARA_SCORING"
    icon = "✅" if apto else "🚫"
    st.markdown(f"{icon} **Calidad de datos:** {calidad.veredicto} ({calidad.completitud_pct}% completo)")
    if calidad.campos_no_confiables:
        with st.expander(f"{len(calidad.campos_no_confiables)} campo(s) no confiable(s)"):
            for c in calidad.campos_no_confiables:
                st.markdown(f"- **{c.campo}**: {c.motivo}")


def _show_veredicto_badge(resultado: str) -> None:
    colores = {
        "APROBADO": "green",
        "APROBADO_CON_CONDICIONES": "orange",
        "RECHAZADO": "red",
        "OBSERVADO": "orange",
        "NO_EVALUABLE": "gray",
    }
    color = colores.get(resultado, "gray")
    st.markdown(f"### :{color}[**{resultado.replace('_', ' ')}**]")


def _show_resultado_badge(resultado: str) -> None:
    colores = {
        "APROBADO": "green",
        "APROBADO_CON_CONDICIONES": "orange",
        "RECHAZADO": "red",
        "NO_EVALUABLE": "gray",
    }
    color = colores.get(resultado, "gray")
    st.markdown(f":{color}[**{resultado.replace('_', ' ')}**] — crédito a 30 días")


def _show_hechos(hechos) -> None:
    cv = hechos.composicion_ventas
    piva = hechos.postergaciones_iva

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Composición de ventas**")
        if cv.pct_facturado is not None:
            st.markdown(f"- {cv.pct_facturado:.0%} facturado / {cv.pct_boletas:.0%} boleta")
            st.markdown(f"- {cv.meses_evaluados} meses evaluados")
        else:
            st.markdown("- Sin datos de facturación en el período evaluado")
        if cv.nota:
            st.caption(cv.nota)
    with col2:
        st.markdown("**Postergaciones de IVA**")
        st.markdown(
            f"- {piva.meses_con_postergacion} de {piva.total_meses_evaluados} meses "
            "con postergación declarada"
        )
        if piva.periodos:
            st.caption(f"Períodos: {', '.join(piva.periodos)}")


def _show_indicador(titulo: str, indicador) -> None:
    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric(titulo, f"{indicador.score}/100" if indicador.score is not None else "—")
    with col2:
        st.markdown(_CONFIANZA_LABEL.get(indicador.confianza, indicador.confianza))
        st.caption(indicador.criterio)
