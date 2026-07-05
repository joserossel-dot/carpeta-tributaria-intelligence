import streamlit as st
import pandas as pd

from app.utils.formatting import fmt_date
from src.models.tax_folder import TaxFolder


def show_corporate_info(tax_folder: TaxFolder) -> None:
    st.subheader("Socios y Administración")
    c = tax_folder.corporate
    if not c:
        st.info("No se encontró información societaria.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Tipo de sociedad**  \n{c.tipo_sociedad or '—'}")
    with col2:
        st.markdown(f"**Fecha de constitución**  \n{fmt_date(c.fecha_constitucion)}")
    with col3:
        st.markdown(f"**Capital**  \n{c.capital or '—'}")

    if c.socios:
        st.markdown("### Socios")
        socios_rows = []
        for s in c.socios:
            socios_rows.append({
                "RUT": s.rut,
                "Nombre": s.nombre,
                "Participación": f"{s.participacion}%" if s.participacion else "—",
            })
        st.dataframe(pd.DataFrame(socios_rows), width="stretch", hide_index=True)

    if c.representantes:
        st.markdown("### Representantes Legales")
        repr_rows = []
        for r in c.representantes:
            repr_rows.append({
                "RUT": r.rut,
                "Nombre": r.nombre,
                "Cargo": r.cargo or "—",
            })
        st.dataframe(pd.DataFrame(repr_rows), width="stretch", hide_index=True)

    if not c.socios and not c.representantes:
        st.info("No se encontraron socios ni representantes.")
