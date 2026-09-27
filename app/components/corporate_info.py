import streamlit as st
import pandas as pd

from app.utils.formatting import fmt_date
from src.models.tax_folder import TaxFolder


def show_corporate_info(tax_folder: TaxFolder) -> None:
    st.subheader("Socios y Administración")
    c = getattr(tax_folder, "corporate", None)
    if not c:
        st.info("No se encontró información societaria.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Tipo de sociedad**  \n{getattr(c, 'tipo_sociedad', None) or '—'}")
    with col2:
        st.markdown(f"**Fecha de constitución**  \n{fmt_date(getattr(c, 'fecha_constitucion', None))}")
    with col3:
        st.markdown(f"**Capital**  \n{getattr(c, 'capital', None) or '—'}")

    socios = getattr(c, "socios", []) or []
    if socios:
        st.markdown("### Socios")
        socios_rows = []
        for s in socios:
            part = getattr(s, "participacion", None)
            socios_rows.append({
                "RUT": getattr(s, "rut", "—"),
                "Nombre": getattr(s, "nombre", "—"),
                "Participación": f"{part}%" if part is not None else "—",
            })
        st.dataframe(pd.DataFrame(socios_rows), width="stretch", hide_index=True)

    representantes = getattr(c, "representantes", []) or []
    if representantes:
        st.markdown("### Representantes Legales")
        repr_rows = []
        for r in representantes:
            repr_rows.append({
                "RUT": getattr(r, "rut", "—"),
                "Nombre": getattr(r, "nombre", "—"),
                "Cargo": getattr(r, "cargo", None) or "—",
            })
        st.dataframe(pd.DataFrame(repr_rows), width="stretch", hide_index=True)

    if not socios and not representantes:
        st.info("No se encontraron socios ni representantes.")
