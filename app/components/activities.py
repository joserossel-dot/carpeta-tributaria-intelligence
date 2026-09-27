import streamlit as st
import pandas as pd

from app.utils.formatting import fmt_date
from src.models.tax_folder import TaxFolder


def show_activities(tax_folder: TaxFolder) -> None:
    st.subheader("Actividades")
    activities = getattr(tax_folder, "activities", []) or []
    if not activities:
        st.info("No se encontraron actividades económicas.")
        return

    rows = []
    for a in activities:
        rows.append({
            "Código": getattr(a, "codigo", "—"),
            "Descripción": getattr(a, "descripcion", "—"),
            "Principal": "Sí" if getattr(a, "principal", False) else "No",
            "Categoría": getattr(a, "categoria", "") or "",
            "Inicio": fmt_date(getattr(a, "fecha_inicio", None)),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True)
