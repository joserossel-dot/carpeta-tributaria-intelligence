import streamlit as st

from app.components.activities import show_activities
from app.components.alerts import show_alerts
from app.components.company_info import show_company_info
from app.components.corporate_info import show_corporate_info
from app.components.downloads import show_downloads
from app.components.export_data import show_export
from app.components.f22_summary import show_f22_summary
from app.components.kpi_cards import show_kpi_cards
from app.components.monthly_chart import show_monthly_chart
from app.components.representatives import show_representatives
from app.utils.pdf_processor import process_pdf

st.set_page_config(
    page_title="Carpeta Tributaria",
    page_icon="📁",
    layout="wide",
)

st.title("Carpeta Tributaria")
st.markdown("Sube el PDF de la Carpeta Tributaria para obtener el análisis.")

uploaded_file = st.file_uploader(
    "Arrastra un PDF aquí",
    type=["pdf"],
    accept_multiple_files=False,
)

if uploaded_file is not None and st.button("Analizar", type="primary"):
    with st.spinner("Procesando Carpeta Tributaria..."):
        try:
            result, json_bytes, markdown_bytes = process_pdf(uploaded_file)
        except Exception as e:
            st.error(f"Error al procesar el PDF: {e}")
            st.stop()

    st.success(
        f"Procesado en {result.metadata.processing_time}s "
        f"({result.metadata.pages} páginas)"
    )

    show_kpi_cards(result)
    st.divider()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["Empresa", "Socios y Administración", "IVA Mensual", "F22", "Alertas", "Exportación"]
    )

    with tab1:
        show_company_info(result)
        st.divider()
        show_activities(result)
        st.divider()
        show_representatives(result.representatives)

    with tab2:
        show_corporate_info(result)

    with tab3:
        show_monthly_chart(result)

    with tab4:
        show_f22_summary(result)

    with tab5:
        show_alerts(result)

    with tab6:
        show_export(result)

    st.divider()
    show_downloads(json_bytes, markdown_bytes)
