import streamlit as st

from src.models.tax_folder import TaxFolder


def show_alerts(tax_folder: TaxFolder) -> None:
    st.subheader("Alertas")
    if not tax_folder.validation:
        st.info("No existen alertas implementadas.")
        return

    for v in tax_folder.validation:
        icon = {"info": "ℹ️", "warning": "⚠️", "error": "🚫", "critical": "🔥"}
        label = icon.get(v.severity.value if hasattr(v.severity, 'value') else v.severity, "ℹ️")
        with st.expander(f"{label} **{v.title}**", expanded=True):
            st.markdown(f"**{v.code}** — {v.description}")
            if v.recommendation:
                st.markdown(f"*Recomendación:* {v.recommendation}")
