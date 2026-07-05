import streamlit as st

from app.utils.formatting import fmt_currency, fmt_miles
from src.models.tax_folder import TaxFolder


def show_kpi_cards(tax_folder: TaxFolder) -> None:
    ma = tax_folder.monthly_analysis
    kpis = tax_folder.kpis

    ventas_12m = ma.ventas_ultimos_12 if ma and ma.ventas_ultimos_12 is not None else None
    compras_12m = ma.compras_ultimos_12 if ma and ma.compras_ultimos_12 is not None else None
    prom_ventas = ma.promedio_ventas_mensual if ma and ma.promedio_ventas_mensual is not None else None
    prom_compras = ma.promedio_compras_mensual if ma and ma.promedio_compras_mensual is not None else None
    cant_f29 = kpis.f29_count if kpis else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Ventas últimos 12 meses", fmt_currency(ventas_12m))
    with col2:
        st.metric("Compras últimos 12 meses", fmt_currency(compras_12m))
    with col3:
        st.metric("Promedio ventas mensual", fmt_currency(prom_ventas))
    with col4:
        st.metric("Promedio compras mensual", fmt_currency(prom_compras))
    with col5:
        st.metric("F29 procesados", str(cant_f29))
