import streamlit as st
import tempfile
import os
import pandas as pd
from core.tax_folder_engine import TaxFolderEngine

# Configuración visual avanzada
st.set_page_config(
    page_title="Carpeta Tributaria Intelligence",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Motor de Inteligencia - Carpeta Tributaria SII")
st.markdown("Extracción unificada de Compras, Ventas, Declaración Anual y Estructura Societaria.")

uploaded_file = st.file_uploader("Sube el PDF de la Carpeta Tributaria Electrónica", type=["pdf"])

if uploaded_file is not None:
    st.info("Analizando el documento semánticamente... Esto puede tomar unos segundos.")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        # Ejecutar tu motor
        engine = TaxFolderEngine(tmp_path)
        result = engine.parse()
        os.unlink(tmp_path)
        
        st.success("¡Análisis estructurado con éxito!")
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 Ventas y Compras (Mes a Mes)", 
            "🏢 Declaración Anual de Impuestos", 
            "👥 Conformación de la Sociedad",
            "💾 JSON Completo"
        ])
        
        # ---------------------------------------------------------
        # PESTAÑA 1: VENTAS Y COMPRAS MES A MES (F29)
        # ---------------------------------------------------------
        with tab1:
            st.subheader("Historial de Compras y Ventas Mensuales (F29)")
            
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
                                
                    f29_data.append({
                        "Período": periodo,
                        "Ventas ($)": monto_ventas,
                        "Compras ($)": monto_compras
                    })
                
                df_f29 = pd.DataFrame(f29_data)
                st.markdown("### Evolución de Flujos")
                st.line_chart(df_f29.set_index("Período"))
                st.markdown("### Detalle Mensual")
                st.dataframe(df_f29, use_container_width=True)
            else:
                st.warning("No se encontraron registros mensuales de F29 en esta carpeta.")

        # ---------------------------------------------------------
        # PESTAÑA 2: DECLARACIÓN ANUAL (Formateada sin JSON crudo)
        # ---------------------------------------------------------
        with tab2:
            st.subheader("Declaración Anual de Impuestos")
            
            if hasattr(result, 'contributor') and result.contributor:
                c = result.contributor
                st.markdown("### Resumen de Clasificación")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Régimen Tributario", getattr(c, 'regimen_tributario', 'No especificado'))
                with col2:
                    st.metric("Tipo de Contribuyente", getattr(c, 'tipo_contribuyente', 'No especificado'))
                with col3:
                    st.metric("Inicio de Actividades", getattr(c, 'fecha_inicio_actividades', 'No especificado'))
            
            st.markdown("### Datos de la Declaración Anual")
            # Si el análisis anual viene dentro de 'analysis' o 'f22', lo desplegamos de forma amigable
            analysis_data = getattr(result, 'analysis', None) or getattr(result, 'f22', None)
            
            if analysis_data:
                # Si es un diccionario, lo iteramos para mostrarlo lindo como tarjetas en lugar de un JSON crudo
                if isinstance(analysis_data, dict):
                    for clave, valor in analysis_data.items():
                        # Reemplazamos guiones bajos por espacios y ponemos mayúsculas
                        titulo_bonito = clave.replace("_", " ").title()
                        st.markdown(f"**{titulo_bonito}**")
                        st.info(str(valor))
                else:
                    st.info(str(analysis_data))
            else:
                st.warning("No se detectaron datos adicionales de la declaración anual en el procesamiento base.")

        # ---------------------------------------------------------
        # PESTAÑA 3: CONFORMACIÓN DE LA SOCIEDAD
        # ---------------------------------------------------------
        with tab3:
            st.subheader("Conformación de la Sociedad")
            
            # Buscamos de manera flexible: ya sea en 'representatives', 'society', o 'shares'
            socios = getattr(result, 'representatives', None) or getattr(result, 'society', None) or getattr(result, 'conformacion_sociedad', None)
            
            if socios and len(socios) > 0:
                rep_data = []
                for r in socios:
                    rep_data.append({
                        "Nombre / Razón Social": getattr(r, 'nombre', getattr(r, 'razon_social', 'N/A')),
                        "RUT": getattr(r, 'rut', 'N/A'),
                        "Participación / Cargo": getattr(r, 'cargo', getattr(r, 'participacion', 'Socio/Representante'))
                    })
                df_rep = pd.DataFrame(rep_data)
                st.dataframe(df_rep, use_container_width=True)
            else:
                st.warning("El motor parseó el documento pero la estructura de 'Conformación de la sociedad' no devolvió registros. Revisa el contrato en la pestaña 'JSON Completo' para ver bajo qué nombre exacto de variable está guardando estos datos tu pipeline.")

        # ---------------------------------------------------------
        # PESTAÑA 4: JSON COMPLETO (Para auditoría técnica)
        # ---------------------------------------------------------
        with tab4:
            st.subheader("Contrato Único de Salida (Pydantic)")
            json_str = result.model_dump_json(indent=2, ensure_ascii=False)
            st.json(json_str)

    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        st.error(f"Error en el pipeline de inteligencia: {str(e)}")
