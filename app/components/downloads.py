import streamlit as st
from src.models.tax_folder import TaxFolder
from src.reports.excel_report import ExcelReport
from src.reports.pdf_report import PDFReport


def show_downloads(target: TaxFolder | bytes, markdown_bytes: bytes | None = None) -> None:
    """Muestra los botones de descarga de Informe de Riesgo en PDF y Cartola de Evaluación en Excel."""
    st.subheader("Descarga de Informes y Cartola de Evaluación")
    st.caption("Cifras en Miles de Pesos Chilenos (M$). Procesamiento seguro en memoria temporal.")

    if isinstance(target, TaxFolder):
        tf = target
    else:
        tf = getattr(st.session_state, "result", None)

    if tf is not None and isinstance(tf, TaxFolder):
        rut_val = getattr(getattr(tf, "contributor", None), "rut", "empresa") or "empresa"
        rut_clean = str(rut_val).replace(".", "").replace("-", "").strip()

        pdf_data = PDFReport().generate(tf)
        excel_data = ExcelReport().generate(tf)

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📄 Descargar Informe de Evaluación Tributaria (PDF)",
                data=pdf_data,
                file_name=f"evaluacion_tributaria_{rut_clean}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with col2:
            st.download_button(
                label="📊 Descargar Cartola de Evaluación (Excel .xlsx)",
                data=excel_data,
                file_name=f"cartola_evaluacion_{rut_clean}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    else:
        st.info("No hay información de carpeta disponible para generar descargas ejecutivas.")
