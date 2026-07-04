import streamlit as st
import tempfile
import os
from core.tax_folder_engine import TaxFolderEngine

st.set_page_config(
    page_title="Carpeta Tributaria Intelligence",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Motor de Inteligencia - Carpeta Tributaria SII")
st.markdown("Sube el PDF de la Carpeta Tributaria Electrónica para extraer y unificar su información.")

uploaded_file = st.file_uploader("Arrastra o selecciona el PDF de la Carpeta Tributaria", type=["pdf"])

if uploaded_file is not None:
    st.info("Procesando archivo... Esto puede tomar unos segundos.")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        engine = TaxFolderEngine(tmp_path)
        result = engine.parse()
        os.unlink(tmp_path)
        st.success("¡Extracción completada con éxito!")
        
        tab1, tab2, tab3 = st.tabs(["🏢 Resumen Contribuyente", "📈 Datos F29 / KPIs", "💾 JSON Estructurado"])
        
        with tab1:
            st.subheader("Datos del Contribuyente")
            if hasattr(result, 'contributor') and result.contributor:
                c = result.contributor
                st.text(f"RUT: {getattr(c, 'rut', 'No detectado')}")
                st.text(f"Razón Social: {getattr(c, 'razon_social', 'No detectado')}")
                st.text(f"Régimen Tributario: {getattr(c, 'regimen_tributario', 'No detectado')}")
                st.text(f"Comuna: {getattr(c, 'comuna', 'No detectado')}")
            else:
                st.warning("No se encontraron metadatos del contribuyente.")
                
        with tab2:
            st.subheader("Análisis y KPIs Detectados")
            if hasattr(result, 'kpis') and result.kpis:
                st.json(result.kpis)
            else:
                st.info("Sección de KPIs vacía o en desarrollo.")
                
        with tab3:
            st.subheader("Contrato Único de Salida (JSON)")
            json_str = result.model_dump_json(indent=2, ensure_ascii=False)
            st.json(json_str)
            st.download_button(
                label="📥 Descargar JSON",
                data=json_str,
                file_name="carpeta_extraida.json",
                mime="application/json"
            )
            
    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        st.error(f"Hubo un error al procesar el PDF: {str(e)}")
