import streamlit as st
import pandas as pd

from app.utils.formatting import fmt_currency
from src.models.tax_folder import TaxFolder


def show_monthly_chart(tax_folder: TaxFolder) -> None:
    st.subheader("IVA mensual")
    monthly_taxes = getattr(tax_folder, "monthly_taxes", []) or []
    if not monthly_taxes:
        st.info("No se encontraron datos de IVA mensual.")
        return

    rows = []
    for mt in monthly_taxes:
        t_ventas = getattr(mt, "total_ventas", None)
        t_compras = getattr(mt, "compras", None)
        ventas = float(t_ventas) if t_ventas is not None else 0.0
        compras = float(t_compras) if t_compras is not None else 0.0
        rows.append({
            "Período": getattr(mt, "periodo", ""),
            "Ventas": ventas,
            "Compras": compras,
            "_ventas_str": fmt_currency(t_ventas),
            "_compras_str": fmt_currency(t_compras),
        })

    df = pd.DataFrame(rows)
    df["Período"] = pd.Categorical(df["Período"], categories=df["Período"], ordered=True)

    st.line_chart(
        df.set_index("Período")[["Ventas", "Compras"]],
        width="stretch",
    )

    st.dataframe(
        df[["Período", "_ventas_str", "_compras_str"]].rename(
            columns={"_ventas_str": "Ventas", "_compras_str": "Compras"}
        ),
        width="stretch",
        hide_index=True,
    )
