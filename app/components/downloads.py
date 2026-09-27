import streamlit as st
from src.models.tax_folder import TaxFolder
from src.reports.excel_report import ExcelReport
from src.reports.pdf_report import PDFReport


def show_downloads(target: TaxFolder | bytes, markdown_bytes: bytes | None = None) -> None:
    """Muestra los botones de descarga de Dictamen Ejecutivo en PDF y Cartola en Excel.
    
    Generación 100% en memoria RAM (Zero-PII) sin tocar disco.
    """
    st.subheader("Descargas Ejecutivas de Comité (Zero-PII)")
    st.caption("Documentos oficiales generados en memoria volátil conforme a la Ley 21.719.")

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
                label="📄 Descargar Dictamen Ejecutivo (PDF)",
                data=pdf_data,
                file_name=f"dictamen_comite_{rut_clean}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with col2:
            st.download_button(
                label="📊 Descargar Cartola y Dictamen (Excel .xlsx)",
                data=excel_data,
                file_name=f"cartola_dictamen_{rut_clean}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    else:
        st.info("No hay información de carpeta disponible para generar descargas ejecutivas.")
