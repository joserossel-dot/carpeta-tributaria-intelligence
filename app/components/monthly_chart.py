import streamlit as st
import pandas as pd

from app.utils.formatting import format_mclp
from src.models.tax_folder import TaxFolder


def show_monthly_chart(tax_folder: TaxFolder) -> None:
    st.subheader("IVA Mensual — Dinámica de Ventas y Compras (M$)")
    monthly_taxes = getattr(tax_folder, "monthly_taxes", []) or []
    if not monthly_taxes:
        st.info("No se encontraron datos de IVA mensual.")
        return

    rows = []
    for mt in monthly_taxes:
        t_ventas = getattr(mt, "total_ventas", None)
        t_compras = getattr(mt, "compras", None)
        ventas_m = (float(t_ventas) / 1000.0) if t_ventas is not None else 0.0
        compras_m = (float(t_compras) / 1000.0) if t_compras is not None else 0.0
        rows.append({
            "Período": getattr(mt, "periodo", ""),
            "Ventas (M$)": round(ventas_m, 1),
            "Compras (M$)": round(compras_m, 1),
            "_ventas_str": format_mclp(t_ventas),
            "_compras_str": format_mclp(t_compras),
        })

    df = pd.DataFrame(rows)
    df["Período"] = pd.Categorical(df["Período"], categories=df["Período"], ordered=True)

    st.line_chart(
        df.set_index("Período")[["Ventas (M$)", "Compras (M$)"]],
        width="stretch",
    )

    st.dataframe(
        df[["Período", "_ventas_str", "_compras_str"]].rename(
            columns={"_ventas_str": "Ventas (M$)", "_compras_str": "Compras (M$)"}
        ),
        width="stretch",
        hide_index=True,
    )
    st.caption("ℹ️ Cifras expresadas en Miles de Pesos Chilenos (M$)")

