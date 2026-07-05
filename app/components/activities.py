import streamlit as st
import pandas as pd

from app.utils.formatting import fmt_date
from src.models.tax_folder import TaxFolder


def show_activities(tax_folder: TaxFolder) -> None:
    st.subheader("Actividades")
    if not tax_folder.activities:
        st.info("No se encontraron actividades económicas.")
        return

    rows = []
    for a in tax_folder.activities:
        rows.append({
            "Código": a.codigo,
            "Descripción": a.descripcion,
            "Principal": "Sí" if a.principal else "No",
            "Categoría": a.categoria or "",
            "Inicio": fmt_date(a.fecha_inicio),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True)
