import streamlit as st
import pandas as pd

from app.utils.formatting import fmt_currency
from src.models.tax_folder import TaxFolder


def show_monthly_chart(tax_folder: TaxFolder) -> None:
    st.subheader("IVA mensual")
    if not tax_folder.monthly_taxes:
        st.info("No se encontraron datos de IVA mensual.")
        return

    rows = []
    for mt in tax_folder.monthly_taxes:
        ventas = float(mt.total_ventas) if mt.total_ventas is not None else 0.0
        compras = float(mt.compras) if mt.compras is not None else 0.0
        rows.append({
            "Período": mt.periodo,
            "Ventas": ventas,
            "Compras": compras,
            "_ventas_str": fmt_currency(mt.total_ventas),
            "_compras_str": fmt_currency(mt.compras),
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
