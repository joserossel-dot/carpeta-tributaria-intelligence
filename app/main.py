import gc
import os
import streamlit as st

from app.components.activities import show_activities
from app.components.alerts import show_alerts
from app.components.company_info import show_company_info
from app.components.corporate_info import show_corporate_info
from app.components.credit_score import show_credit_score
from app.components.downloads import show_downloads
from app.components.export_data import show_export
from app.components.f22_summary import show_f22_summary
from app.components.kpi_cards import show_kpi_cards
from app.components.monthly_chart import show_monthly_chart
from app.components.representatives import show_representatives
from app.utils.pdf_processor import process_pdf

# 1. Configuración de Marca Blanca y Paginación
st.set_page_config(
    page_title="Cavilaria | Comité de Crédito B2B",
    page_icon="🏢",
    layout="wide",
)

# 2. Inyección CSS para incrustación Iframe limpia (WordPress)
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 3. Encabezado Ejecutivo Institucional Cavilaria SpA
st.markdown(
    """
    <div style="padding: 0.5rem 0 1.25rem 0; border-bottom: 2px solid #E2E8F0; margin-bottom: 1.5rem;">
      <h1 style="color: #0F172A; margin: 0; font-size: 1.85rem; font-weight: 800; letter-spacing: -0.5px;">
        CAVILARIA SpA — Comité de Crédito y Riesgo B2B
      </h1>
      <p style="color: #64748B; margin: 0.35rem 0 0 0; font-size: 0.95rem;">
        Motor cuantitativo de evaluación de riesgo comercial y asignación de cupo.
        <span style="display: inline-block; margin-left: 8px; padding: 2px 8px; background: #EEF2F6; border-radius: 4px; font-size: 0.85rem; color: #1E293B;">
          🔒 Sello de <strong>Retención Cero (Ley N° 21.719)</strong> — 
          <a href="https://cavilaria.com/politica-de-privacidad/" target="_blank" style="color: #0284C7; text-decoration: underline; font-weight: 500;">
            Política de Privacidad
          </a>
        </span>
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# 4. Gate de Acceso Comercial y Roles
CLIENT_CODE = os.environ.get("CAVILARIA_CLIENT_CODE", "CAVILARIA2026").strip()
ADMIN_CODE = os.environ.get("CAVILARIA_ADMIN_CODE", "ADMIN-CAVILARIA-99").strip()

if "auth_role" not in st.session_state:
    st.markdown("### 🔐 Acceso Corporativo")
    st.markdown(
        "Ingrese su código de autorización comercial para acceder a la plataforma "
        "de evaluación crediticia de **Cavilaria SpA**."
    )
    with st.form("auth_form"):
        codigo_input = st.text_input(
            "🔑 Código de Acceso Corporativo",
            type="password",
            placeholder="Ingrese código corporativo...",
        )
        submit_btn = st.form_submit_button("Ingresar al Comité", type="primary")

        if submit_btn:
            codigo_clean = codigo_input.strip()
            if codigo_clean == ADMIN_CODE:
                st.session_state["auth_role"] = "admin"
                st.rerun()
            elif codigo_clean == CLIENT_CODE:
                st.session_state["auth_role"] = "client"
                st.rerun()
            else:
                st.error("Código no autorizado. Por favor contacte a su ejecutivo de Cavilaria SpA.")
    st.stop()

auth_role = st.session_state.get("auth_role", "client")

# Barra de estado de usuario autenticado
col_auth_info, col_auth_action = st.columns([5, 1])
with col_auth_info:
    if auth_role == "admin":
        st.caption("🛡️ **Nivel:** Administrador Cavilaria (Benchmark habilitado)")
    else:
        st.caption("👤 **Nivel:** Cliente Corporativo Autorizado")
with col_auth_action:
    if st.button("Cerrar Sesión", key="btn_logout"):
        st.session_state.clear()
        gc.collect()
        st.rerun()

st.divider()

# 5. Entrada de Documento y Cupo Solicitado
uploaded_file = st.file_uploader(
    "Arrastra la Carpeta Tributaria PDF aquí",
    type=["pdf"],
    accept_multiple_files=False,
)

st.info(
    "🔒 **Privacidad Garantizada (Zero-PII):** Su PDF se procesa exclusivamente en memoria RAM volátil "
    "y se destruye al instante. No almacenamos RUTs, razones sociales ni documentos. "
    "Solo se procesan coeficientes estadísticos anónimos para calibración sectorial."
)

cupo_solicitado = st.number_input(
    "Cupo de crédito solicitado (CLP, opcional)",
    min_value=0,
    value=0,
    step=1_000_000,
    help="Se usa para calcular el indicador de Respaldo Estructural (Capital "
    "Propio Tributario vs. cupo). Si lo dejas en 0, ese indicador queda sin "
    "calificar.",
)

col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    analizar = st.button("Analizar", type="primary", disabled=uploaded_file is None)
with col_btn2:
    if st.button("🗑️ Limpiar sesión actual"):
        role = st.session_state.get("auth_role")
        st.session_state.clear()
        if role:
            st.session_state["auth_role"] = role
        gc.collect()
        st.rerun()

if uploaded_file is not None and analizar:
    with st.spinner("Procesando Carpeta Tributaria en memoria RAM..."):
        try:
            result, json_bytes, markdown_bytes = process_pdf(
                uploaded_file, cupo_solicitado=cupo_solicitado or None
            )
            st.session_state["result"] = result
            st.session_state["json_bytes"] = json_bytes
            st.session_state["markdown_bytes"] = markdown_bytes
        except Exception as e:
            st.error(f"Error al procesar el PDF: {e}")
            st.stop()

if "result" in st.session_state:
    result = st.session_state["result"]
    json_bytes = st.session_state["json_bytes"]
    markdown_bytes = st.session_state["markdown_bytes"]

    st.success(
        f"Procesado en {result.metadata.processing_time}s "
        f"({result.metadata.pages} páginas)"
    )

    show_kpi_cards(result)
    st.divider()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        [
            "Empresa",
            "Socios y Administración",
            "IVA Mensual",
            "F22",
            "Score Crediticio",
            "Alertas",
            "Exportación",
        ]
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
        show_credit_score(result)

    with tab6:
        show_alerts(result)

    with tab7:
        show_export(result, auth_role=auth_role)

    st.divider()
    show_downloads(json_bytes, markdown_bytes)
