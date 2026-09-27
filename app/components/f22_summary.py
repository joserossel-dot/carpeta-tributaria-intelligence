import streamlit as st
import pandas as pd

from app.utils.formatting import fmt_currency
from src.models.tax_folder import TaxFolder


def show_f22_summary(tax_folder: TaxFolder) -> None:
    st.subheader("F22 — Declaración Anual")
    f22_list = getattr(tax_folder, "f22", []) or []
    if not f22_list:
        st.info("No se encontraron declaraciones anuales (F22).")
        return

    rows = []
    for f in f22_list:
        rows.append({
            "Año tributario": getattr(f, "anio_tributario", "") or "",
            "Ingresos": fmt_currency(getattr(f, "ingresos", None)),
            "Renta líquida imponible": fmt_currency(getattr(f, "renta_liquida_imponible", None)),
            "Capital propio tributario": fmt_currency(getattr(f, "capital_propio_tributario", None)),
            "Impuesto determinado": fmt_currency(getattr(f, "impuesto_determinado", None)),
            "PPM": fmt_currency(getattr(f, "ppm", None)),
            "Créditos": fmt_currency(getattr(f, "creditos", None)),
            "Pérdidas": fmt_currency(getattr(f, "perdidas", None)),
            "Base imponible": fmt_currency(getattr(f, "base_imponible", None)),
            "Resultado tributario": fmt_currency(getattr(f, "resultado_tributario", None)),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True)
