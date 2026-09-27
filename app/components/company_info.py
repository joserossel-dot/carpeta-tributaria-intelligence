import streamlit as st

from app.utils.formatting import fmt_date
from src.models.tax_folder import TaxFolder


def show_company_info(tax_folder: TaxFolder) -> None:
    st.subheader("Empresa")
    c = getattr(tax_folder, "contributor", None)
    if not c:
        st.info("No se encontraron datos del contribuyente.")
        return

    kpis = getattr(tax_folder, "kpis", None)
    principal_act = getattr(kpis, "principal_activity", None) if kpis else "—"

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Razón social**  \n{getattr(c, 'razon_social', None) or '—'}")
        st.markdown(f"**RUT**  \n{getattr(c, 'rut', None) or '—'}")
        st.markdown(f"**Giro principal**  \n{principal_act or '—'}")
    with col2:
        st.markdown(f"**Régimen**  \n{getattr(c, 'regimen_tributario', None) or '—'}")
        st.markdown(f"**Inicio actividades**  \n{fmt_date(getattr(c, 'fecha_inicio_actividades', None))}")
