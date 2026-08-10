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
    st.subheader("Score Crediticio")

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
    col1, col2 = st.columns([1, 2])
    with col1:
        if cr.score_compuesto is not None:
            st.metric("Score compuesto", f"{cr.score_compuesto}/100")
        else:
            st.metric("Score compuesto", "No evaluable")
            st.caption("Menos de 2 de 3 indicadores tienen datos suficientes.")
    with col2:
        if cr.decision.resultado_base:
            _show_resultado_badge(cr.decision.resultado_base)

    st.divider()
    st.markdown("#### Hechos (sin calificar)")
    st.caption("Se reportan tal cual, sin convertirlos en un juicio de riesgo.")
    _show_hechos(cr.hechos)

    st.divider()
    st.markdown("#### Indicadores")
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
