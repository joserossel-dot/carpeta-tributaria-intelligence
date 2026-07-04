import os
import sys
import importlib.util
import streamlit as st
from src.core.tax_folder_engine import TaxFolderEngine

# --- CARGA DIRECTA POR RUTA FÍSICA ---
# Calculamos la ubicación exacta en el disco de Render o en tu PC local
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
file_path = os.path.join(base_dir, "app", "components", "f22_summary.py")

if os.path.exists(file_path):
    # Inyectamos el directorio base en el PATH para que las dependencias internas (app.utils) se resuelvan
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
    
    # Cargamos el archivo de forma manual e individual
    spec = importlib.util.spec_from_file_location("f22_summary_module", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    show_f22_summary = module.show_f22_summary
else:
    def show_f22_summary(*args, **kwargs):
        st.error(f"No se encontró el archivo del componente en: {file_path}")
# -------------------------------------

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
