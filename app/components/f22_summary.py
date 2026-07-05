import streamlit as st
import pandas as pd

from app.utils.formatting import fmt_currency
from src.models.tax_folder import TaxFolder


def show_f22_summary(tax_folder: TaxFolder) -> None:
    st.subheader("F22 — Declaración Anual")
    if not tax_folder.f22:
        st.info("No se encontraron declaraciones anuales (F22).")
        return

    rows = []
    for f in tax_folder.f22:
        rows.append({
            "Año tributario": f.anio_tributario or "",
            "Ingresos": fmt_currency(f.ingresos),
            "Renta líquida imponible": fmt_currency(f.renta_liquida_imponible),
            "Capital propio tributario": fmt_currency(f.capital_propio_tributario),
            "Impuesto determinado": fmt_currency(f.impuesto_determinado),
            "PPM": fmt_currency(f.ppm),
            "Créditos": fmt_currency(f.creditos),
            "Pérdidas": fmt_currency(f.perdidas),
            "Base imponible": fmt_currency(f.base_imponible),
            "Resultado tributario": fmt_currency(f.resultado_tributario),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True)
