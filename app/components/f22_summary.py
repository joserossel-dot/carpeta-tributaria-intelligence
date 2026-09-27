import streamlit as st
import pandas as pd

from app.utils.formatting import format_mclp
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
            "Año": getattr(f, "anio_tributario", "") or "",
            "Ingresos (M$)": format_mclp(getattr(f, "ingresos", None)),
            "RLI (M$)": format_mclp(getattr(f, "renta_liquida_imponible", None)),
            "Capital Propio CPT (M$)": format_mclp(getattr(f, "capital_propio_tributario", None)),
            "Impuesto Determinado (M$)": format_mclp(getattr(f, "impuesto_determinado", None)),
            "PPM (M$)": format_mclp(getattr(f, "ppm", None)),
            "Créditos (M$)": format_mclp(getattr(f, "creditos", None)),
            "Pérdidas (M$)": format_mclp(getattr(f, "perdidas", None)),
            "Base Imponible (M$)": format_mclp(getattr(f, "base_imponible", None)),
            "Resultado Tributario (M$)": format_mclp(getattr(f, "resultado_tributario", None)),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True)
    st.caption("ℹ️ Cifras expresadas en Miles de Pesos Chilenos (M$)")

