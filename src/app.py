import os
import sys
import streamlit as st
from src.core.tax_folder_engine import TaxFolderEngine

# Inyección absoluta para solucionar las rutas internas de los componentes
raiz_real = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if raiz_real not in sys.path:
    sys.path.insert(0, raiz_real)

from components.f22_summary import show_f22_summary

st.set_page_config(
    page_title="Motor de Inteligencia - Carpeta Tributaria",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Motor de Inteligencia - Carpeta Tributaria SII")
st.markdown("Estado de extracción unificada de Compras, Ventas, Renta y Estructura Societaria.")

uploaded_file = st.file_uploader("Sube el PDF de la Carpeta Tributaria Electrónica", type=["pdf"])

if uploaded_file is not None:
    temp_path = f"temp_{uploaded_file.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    try:
        with st.spinner("Procesando Carpeta Tributaria..."):
            engine = TaxFolderEngine(temp_path)
            result = engine.parse()
        
        st.success("✅ Documento procesado con éxito")
        
        tab1, tab2 = st.tabs(["📋 Resumen General", "🏢 Renta Anual (F22)"])
        
        with tab1:
            st.write("Datos generales de la carpeta cargados correctamente.")
            
        with tab2:
            show_f22_summary(result)
            
    except Exception as e:
        st.error(f"❌ Error al procesar el archivo: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
