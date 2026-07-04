import streamlit as st
import tempfile
import os
import pandas as pd
from core.tax_folder_engine import TaxFolderEngine

st.set_page_config(
    page_title="Carpeta Tributaria Intelligence",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Motor de Inteligencia - Carpeta Tributaria SII")
st.markdown("Estado de extracción unificada de Compras, Ventas, Renta y Estructura Societaria.")

uploaded_file = st.file_uploader("Sube el PDF de la Carpeta Tributaria Electrónica", type=["pdf"])

if uploaded_file is not None:
    st.info("Analizando el documento semánticamente... Esto puede tomar unos segundos.")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        engine = TaxFolderEngine(tmp_path)
        result = engine.parse()
        os.unlink(tmp_path)
        
        st.success("¡Documento procesado por el pipeline de arquitectura!")
        
        # Panel de Métricas Rápidas usando tus 'statistics' reales
        st.markdown("### 📊 Estadísticas de Extracción del Motor")
        stats = getattr(result, 'statistics', {}) or {}
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Meses F29 Detectados", stats.get('total_f29', 0))
        with col2:
            st.metric("Actividades Económicas", stats.get('total_actividades', 0))
        with col3:
            st.metric("Socios/Representantes", stats.get('total_representantes', 0))
        with col4:
            st.metric("Bienes (Autos/Propiedades)", stats.get('total_propiedades', 0) + stats.get('total_vehiculos', 0))

        # Alertas del Engine
        warnings = getattr(result, 'warnings', [])
        if warnings:
            for w in warnings:
                st.warning(f"⚠️ Nota del Motor: {w}")

        tab1, tab2, tab3 = st.tabs([
            "📈 Ventas y Compras Mensuales (F29)", 
            "🏢 Declaración Anual de Impuestos", 
            "👥 Conformación de la Sociedad"
        ])
        
        # PESTAÑA 1: MOSTRAR LOS 35 MESES DETECTADOS
        with tab1:
            st.subheader("Historial Mensual de IVA")
            if hasattr(result, 'f29') and result.f29:
                f29_data = []
                for f in result.f29:
                    periodo = getattr(f, 'periodo', 'Desconocido')
                    monto_ventas = 0
                    monto_compras = 0
                    if hasattr(f, 'detalles') and f.detalles:
                        for d in f.detalles:
                            if d.codigo in ["538", "502", "714"]:
                                try: monto_ventas = int(d.valor.replace('.','').replace(',',''))
                                except: pass
                            elif d.codigo in ["537", "519", "520"]:
                                try: monto_compras = int(d.valor.replace('.','').replace(',',''))
                                except: pass
                    f29_data.append({"Período": periodo, "Ventas ($)": monto_ventas, "Compras ($)": monto_compras})
                
                df_f29 = pd.DataFrame(f29_data)
                st.line_chart(df_f29.set_index("Período"))
                st.dataframe(df_f29, use_container_width=True)
            else:
                st.info(f"Se detectaron {stats.get('total_f29', 0)} declaraciones en los metadatos, pero las tablas detalladas están en proceso de mapeo.")

        # PESTAÑA 2: RENTA ANUAL
        with tab2:
            st.subheader("Impuesto a la Renta")
            if hasattr(result, 'contributor') and result.contributor:
                c = result.contributor
                st.markdown(f"**Régimen Tributario Activo:** {getattr(c, 'regimen_tributario', 'No especificado')}")
                st.markdown(f"**Tipo de Contribuyente:** {getattr(c, 'tipo_contribuyente', 'No especificado')}")
            
            st.info("🚧 **Módulo en Desarrollo (Release 0.4):** El motor identificó las secciones anuales de la carpeta tributaria. Los modelos numéricos de impuestos anuales se desplegarán de forma tabulada en la próxima actualización del backend.")

        # PESTAÑA 3: CONFORMACIÓN DE LA SOCIEDAD
        with tab3:
            st.subheader("Estructura Jurídica")
            st.error("🔒 **Sección No Extraída**: El texto de 'Conformación de la sociedad' está presente en el archivo, pero los patrones de expresiones regulares actuales del motor no lograron capturar la estructura de Rut/Nombres.")
            st.markdown("""
            **Próximos pasos para solucionar esto en tu código local:**
            1. Abre tu archivo `src/parsers/contributor_parser.py` (o el parser correspondiente).
            2. Revisa las expresiones regulares (`regex`) que buscan las palabras clave de los socios.
            3. Ajusta el parseador para que capture el formato de las celdas de texto que extrae `pdfplumber`.
            """)

    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        st.error(f"Error en el pipeline: {str(e)}")
