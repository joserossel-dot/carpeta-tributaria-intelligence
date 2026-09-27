import streamlit as st

from app.utils.formatting import format_mclp
from src.models.tax_folder import TaxFolder


def show_kpi_cards(tax_folder: TaxFolder) -> None:
    ma = getattr(tax_folder, "monthly_analysis", None)
    kpis = getattr(tax_folder, "kpis", None)

    ventas_12m = getattr(ma, "ventas_ultimos_12", None)
    compras_12m = getattr(ma, "compras_ultimos_12", None)
    prom_ventas = getattr(ma, "promedio_ventas_mensual", None)
    prom_compras = getattr(ma, "promedio_compras_mensual", None)
    cant_f29 = getattr(kpis, "f29_count", 0)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Ventas 12M", format_mclp(ventas_12m))
    with col2:
        st.metric("Compras 12M", format_mclp(compras_12m))
    with col3:
        st.metric("Prom. ventas mensual", format_mclp(prom_ventas))
    with col4:
        st.metric("Prom. compras mensual", format_mclp(prom_compras))
    with col5:
        st.metric("F29 procesados", str(cant_f29))

    st.caption("ℹ️ Cifras expresadas en Miles de Pesos Chilenos (M$)")
