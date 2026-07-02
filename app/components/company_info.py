import streamlit as st

from app.utils.formatting import fmt_date
from src.models.tax_folder import TaxFolder


def show_company_info(tax_folder: TaxFolder) -> None:
    st.subheader("Empresa")
    c = tax_folder.contributor
    if not c:
        st.info("No se encontraron datos del contribuyente.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Razón social**  \n{c.razon_social or '—'}")
        st.markdown(f"**RUT**  \n{c.rut or '—'}")
        st.markdown(f"**Giro principal**  \n{tax_folder.kpis.principal_activity if tax_folder.kpis and tax_folder.kpis.principal_activity else '—'}")
    with col2:
        st.markdown(f"**Régimen**  \n{c.regimen_tributario or '—'}")
        st.markdown(f"**Inicio actividades**  \n{fmt_date(c.fecha_inicio_actividades)}")
