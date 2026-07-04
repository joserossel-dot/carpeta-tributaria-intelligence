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
        
        # Estructura de pestañas con lo que necesitas ver
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 Ventas y Compras (Mes a Mes)", 
            "🏢 Declaración Anual de Impuestos", 
            "👥 Participación Accionaria / Socios",
            "💾 JSON Completo"
        ])
        
        # ---------------------------------------------------------
        # PESTAÑA 1: VENTAS Y COMPRAS MES A MES (F29)
        # ---------------------------------------------------------
        with tab1:
            st.subheader("Historial de Compras y Ventas Mensuales (F29)")
            
            if hasattr(result, 'f29') and result.f29:
                f29_data = []
                # Recorremos tus registros de F29 extraídos
                for f in result.f29:
                    periodo = getattr(f, 'periodo', 'Desconocido')
                    
                    # Intentamos buscar los códigos típicos de montos de ventas/compras de tus detalles
                    monto_ventas = 0
                    monto_compras = 0
                    
                    if hasattr(f, 'detalles') and f.detalles:
                        for d in f.detalles:
                            # Código 538/502/714 suelen ser totales de ventas en el F29 chileno
                            if d.codigo in ["538", "502", "714"]:
                                try: monto_ventas = int(d.valor.replace('.','').replace(',',''))
                                except: pass
                            # Código 537/519/520 suelen ser totales de compras
                            elif d.codigo in ["537", "519", "520"]:
                                try: monto_compras = int(d.valor.replace('.','').replace(',',''))
                                except: pass
                                
                    f29_data.append({
                        "Período": periodo,
                        "Ventas ($)": monto_ventas,
                        "Compras ($)": monto_compras
                    })
                
                # Crear DataFrame de Pandas para mostrar la tabla y el gráfico
                df_f29 = pd.DataFrame(f29_data)
                
                # Gráfico Evolutivo
                st.markdown("### Evolución de Flujos")
                st.line_chart(df_f29.set_index("Período"))
                
                # Tabla de Datos
                st.markdown("### Detalle Mensual")
                st.dataframe(df_f29, use_container_width=True)
            else:
                st.warning("No se encontraron registros mensuales de F29 en esta carpeta.")

        # ---------------------------------------------------------
        # PESTAÑA 2: DECLARACIÓN ANUAL de IMPUESTOS
        # ---------------------------------------------------------
        with tab2:
            st.subheader("Análisis de Declaración Anual de Impuestos (F22 / Balances)")
            
            # Revisamos si tu engine ya guarda el análisis o la información del régimen
            if hasattr(result, 'contributor') and result.contributor:
                c = result.contributor
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Régimen Tributario", getattr(c, 'regimen_tributario', 'No especificado'))
                with col2:
                    st.metric("Tipo de Contribuyente", getattr(c, 'tipo_contribuyente', 'No especificado'))
            
            if hasattr(result, 'analysis') and result.analysis:
                st.markdown("### Diagnóstico Tributario Inteligente")
                st.json(result.analysis)
            else:
                st.info("Información de renta anual o balance procesada. Si está vacía, verifica si el PDF contiene las páginas del F22.")

        # ---------------------------------------------------------
        # PESTAÑA 3: PARTICIPACIÓN ACCIONARIA
        # ---------------------------------------------------------
        with tab3:
            st.subheader("Estructura de Socios y Participación Accionaria")
            
            # Buscamos en representantes o si tienes un modelo de socios separado
            if hasattr(result, 'representatives') and result.representatives:
                rep_data = []
                for r in result.representatives:
                    rep_data.append({
                        "Nombre / Razón Social": getattr(r, 'nombre', 'N/A'),
                        "RUT": getattr(r, 'rut', 'N/A'),
                        "Rol / Participación": getattr(r, 'cargo', 'Representante Legal')
                    })
                df_rep = pd.DataFrame(rep_data)
                st.table(df_rep)
            else:
                st.warning("No se detectó la tabla de representantes legales o accionistas directos en el parse principal.")

        # ---------------------------------------------------------
        # PESTAÑA 4: JSON COMPLETO
        # ---------------------------------------------------------
        with tab4:
            st.subheader("Contrato Único de Salida (Pydantic)")
            json_str = result.model_dump_json(indent=2, ensure_ascii=False)
            st.json(json_str)

    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        st.error(f"Error en el pipeline de inteligencia: {str(e)}")
