import streamlit as st

from src.models.tax_folder import TaxFolder


def show_alerts(tax_folder: TaxFolder) -> None:
    st.subheader("Alertas")
    validation = getattr(tax_folder, "validation", []) or []
    if not validation:
        st.info("No existen alertas implementadas.")
        return

    for v in validation:
        icon = {"info": "ℹ️", "warning": "⚠️", "error": "🚫", "critical": "🔥"}
        sev = getattr(v, "severity", "info")
        sev_val = getattr(sev, "value", str(sev))
        label = icon.get(sev_val, "ℹ️")
        title = getattr(v, "title", "Alerta")
        code = getattr(v, "code", "")
        desc = getattr(v, "description", "")
        rec = getattr(v, "recommendation", None)

        with st.expander(f"{label} **{title}**", expanded=True):
            st.markdown(f"**{code}** — {desc}")
            if rec:
                st.markdown(f"*Recomendación:* {rec}")
