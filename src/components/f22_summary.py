import streamlit as st
import streamlit as st
from utils.formatting import fmt_currency

def show_f22_summary(result):
    st.subheader("🏢 Resumen de Renta Anual (Formulario 22)")
    
    if not result or "f22" not in result:
        st.warning("⚠️ No se encontraron datos del Formulario 22 en esta Carpeta Tributaria.")
        return
        
    f22_data = result["f22"]
    
    # Cuadro resumen con métricas clave
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Año Tributario", f22_data.get("anno", "N/A"))
    with col2:
        ingresos = f22_data.get("ingresos_brutos", 0)
        st.metric("Ingresos Brutos Anuales", fmt_currency(ingresos))
    with col3:
        impuesto = f22_data.get("impuesto_pago", 0)
        st.metric("Impuesto a Pago / Devolución", fmt_currency(impuesto))
        
    st.markdown("### 📋 Detalles del Formulario")
    st.json(f22_data)

def show_f22_summary(result):
    st.subheader("🏢 Resumen de Renta Anual (Formulario 22)")
    
    if not result or "f22" not in result:
        st.warning("⚠️ No se encontraron datos del Formulario 22 en esta Carpeta Tributaria.")
        return
        
    f22_data = result["f22"]
    
    # Cuadro resumen con métricas clave
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Año Tributario", f22_data.get("anno", "N/A"))
    with col2:
        ingresos = f22_data.get("ingresos_brutos", 0)
        st.metric("Ingresos Brutos Anuales", fmt_currency(ingresos))
    with col3:
        impuesto = f22_data.get("impuesto_pago", 0)
        st.metric("Impuesto a Pago / Devolución", fmt_currency(impuesto))
        
    st.markdown("### 📋 Detalles del Formulario")
    st.json(f22_data)
