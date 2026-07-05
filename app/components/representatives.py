import streamlit as st
import pandas as pd


def show_representatives(representatives: list) -> None:
    st.subheader("Representantes")
    if not representatives:
        st.info("No se encontraron representantes legales.")
        return

    if isinstance(representatives[0], dict):
        df = pd.DataFrame(representatives)
    else:
        rows = []
        for r in representatives:
            if hasattr(r, "model_dump"):
                rows.append(r.model_dump())
            elif hasattr(r, "__dict__"):
                rows.append(r.__dict__)
            else:
                rows.append({"representante": str(r)})
        df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
