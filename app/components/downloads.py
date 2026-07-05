import streamlit as st


def show_downloads(json_bytes: bytes, markdown_bytes: bytes) -> None:
    st.subheader("Descargas")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Descargar JSON",
            data=json_bytes,
            file_name="carpeta_tributaria.json",
            mime="application/json",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            label="Descargar Reporte Markdown",
            data=markdown_bytes,
            file_name="reporte.md",
            mime="text/markdown",
            use_container_width=True,
        )
