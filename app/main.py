import gc
import hashlib
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
from app.utils.formatting import format_mclp
from app.utils.pdf_processor import process_pdf
from src.leads.lead_manager import LeadManager, validar_email

# 1. Configuración de Marca Blanca y Paginación
st.set_page_config(
    page_title="Cavilaria | Evaluación Tributaria y Crédito B2B",
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
        CAVILARIA SpA — Evaluación Tributaria y Recomendación de Crédito Comercial
      </h1>
      <p style="color: #64748B; margin: 0.35rem 0 0 0; font-size: 0.95rem;">
        Motor cuantitativo de evaluación tributaria y recomendación de línea de crédito comercial B2B.
        <span style="display: inline-block; margin-left: 8px; padding: 2px 8px; background: #EEF2F6; border-radius: 4px; font-size: 0.85rem; color: #1E293B;">
          🔒 Cumplimiento <strong>Ley N° 21.719</strong> — 
          <a href="https://cavilaria.com/politica-de-privacidad/" target="_blank" style="color: #0284C7; text-decoration: underline; font-weight: 500;">
            Política de Privacidad
          </a>
        </span>
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# 4. Gate de Acceso Dual: Freemium Autoatendido (2 Evaluaciones) + Clave Corporativa
CLIENT_CODE = os.environ.get("CAVILARIA_CLIENT_CODE", "CAVILARIA2026").strip()
ADMIN_CODE = os.environ.get("CAVILARIA_ADMIN_CODE", "ADMIN-CAVILARIA-99").strip()

if not st.session_state.get("authenticated", False):
    tab_free, tab_code = st.tabs(
        [
            "🚀 Acceso Inmediato: Prueba Gratuita (2 Evaluaciones)",
            "🔑 Ya tengo Código de Cliente / Socio",
        ]
    )

    with tab_free:
        st.markdown("#### Activa tu Prueba Gratuita (2 Evaluaciones)")
        st.markdown(
            "Ingresa tus datos comerciales para evaluar hasta **2 Carpetas Tributarias completas** "
            "sin costo y obtener la recomendación cuantitativa de crédito al instante."
        )
        with st.form("free_trial_form"):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                nombre = st.text_input("Nombre completo *", placeholder="Ej. Juan Pérez")
                empresa = st.text_input("Empresa *", placeholder="Ej. Distribuidora del Norte SpA")
            with col_f2:
                email = st.text_input(
                    "Correo electrónico corporativo *",
                    placeholder="juan.perez@empresa.cl",
                )
                telefono = st.text_input(
                    "Teléfono / WhatsApp (opcional)",
                    placeholder="+56 9 1234 5678",
                )

            submit_free = st.form_submit_button(
                "Activar Acceso Gratuito Ahora", type="primary"
            )

            if submit_free:
                if not nombre.strip():
                    st.error("Por favor ingresa tu nombre completo.")
                elif not empresa.strip():
                    st.error("Por favor ingresa el nombre de tu empresa.")
                elif not validar_email(email):
                    st.error("Por favor ingresa un correo electrónico válido.")
                else:
                    try:
                        lm = LeadManager()
                        lm.registrar_lead(
                            nombre=nombre,
                            empresa=empresa,
                            email=email,
                            telefono=telefono,
                        )
                    except Exception:
                        pass

                    st.session_state["authenticated"] = True
                    st.session_state["access_tier"] = "FREE_TRIAL"
                    st.session_state["free_credits_remaining"] = 2
                    st.session_state["evaluated_fingerprints"] = []
                    st.session_state["user_info"] = {
                        "nombre": nombre.strip(),
                        "empresa": empresa.strip(),
                        "email": email.strip().lower(),
                    }
                    st.rerun()

    with tab_code:
        st.markdown("#### Acceso Corporativo con Clave")
        st.markdown(
            "Si tu empresa ya cuenta con una suscripción comercial o clave de socio, "
            "ingrésala a continuación para acceder sin límites:"
        )
        with st.form("code_form"):
            codigo_input = st.text_input(
                "🔑 Código de Cliente / Administrador",
                type="password",
                placeholder="Ingrese su clave corporativa...",
            )
            submit_code = st.form_submit_button("Ingresar con Código", type="primary")

            if submit_code:
                clean_code = codigo_input.strip()
                if clean_code == ADMIN_CODE:
                    st.session_state["authenticated"] = True
                    st.session_state["access_tier"] = "ADMIN"
                    st.session_state["free_credits_remaining"] = 999999
                    st.rerun()
                elif clean_code == CLIENT_CODE:
                    st.session_state["authenticated"] = True
                    st.session_state["access_tier"] = "CLIENT"
                    st.session_state["free_credits_remaining"] = 999999
                    st.rerun()
                else:
                    st.error(
                        "Código no autorizado. Por favor contacte a su ejecutivo de Cavilaria SpA."
                    )
    st.stop()

access_tier = st.session_state.get("access_tier", "FREE_TRIAL")
free_credits = st.session_state.get("free_credits_remaining", 0)

# Barra de estado y nivel de acceso
col_auth_info, col_auth_action = st.columns([5, 1])
with col_auth_info:
    if access_tier == "ADMIN":
        st.caption("🛡️ **Nivel:** Administrador Cavilaria (Evaluaciones ilimitadas + Benchmark y Leads)")
    elif access_tier == "CLIENT":
        st.caption("👤 **Nivel:** Cliente Corporativo (Evaluaciones ilimitadas)")
    else:
        st.info(f"🎁 **Modo Prueba Gratuita:** Te quedan **{free_credits}** evaluación(es) disponible(s).")
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
    "🔒 **Privacidad (Ley N° 21.719):** Los documentos se procesan exclusivamente en memoria temporal para generar este análisis y no son almacenados por Cavilaria SpA."
)

col_cupo1, col_cupo2 = st.columns([3, 1])
with col_cupo1:
    cupo_solicitado = st.number_input(
        "Cupo de crédito solicitado (CLP, opcional)",
        min_value=0,
        value=0,
        step=500_000,
        help="Se usa para calcular el indicador de Respaldo Estructural (Capital "
        "Propio Tributario vs. cupo). Si lo dejas en 0, ese indicador queda sin "
        "calificar.",
    )
with col_cupo2:
    st.caption("Equivalencia en M$")
    st.markdown(f"**{format_mclp(cupo_solicitado) if cupo_solicitado else 'M$ 0'}**")

col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    analizar = st.button("Analizar", type="primary", disabled=uploaded_file is None)
with col_btn2:
    if st.button("🗑️ Limpiar sesión actual"):
        tier = st.session_state.get("access_tier")
        credits = st.session_state.get("free_credits_remaining")
        fps = st.session_state.get("evaluated_fingerprints")
        uinfo = st.session_state.get("user_info")

        st.session_state.clear()

        st.session_state["authenticated"] = True
        st.session_state["access_tier"] = tier
        st.session_state["free_credits_remaining"] = credits
        st.session_state["evaluated_fingerprints"] = fps
        st.session_state["user_info"] = uinfo
        gc.collect()
        st.rerun()

# 6. Ejecución del Análisis y Control de Créditos
if uploaded_file is not None and analizar:
    file_bytes = uploaded_file.getvalue()
    # Huella criptográfica rápida del archivo para no descontar créditos si solo cambia el cupo solicitado
    file_fp = hashlib.sha256(file_bytes[:4096] + str(len(file_bytes)).encode()).hexdigest()[:16]
    evaluated_fps = st.session_state.get("evaluated_fingerprints", [])
    is_distinct_file = file_fp not in evaluated_fps

    if access_tier == "FREE_TRIAL" and is_distinct_file and free_credits <= 0:
        st.error(
            "⚠️ **Límite de Prueba Gratuita Alcanzado (2/2)**\n\n"
            "Has completado tus 2 evaluaciones gratuitas. Para continuar analizando nuevas carpetas "
            "tributarias sin límites, activa tu suscripción corporativa contactando a **contacto@cavilaria.com** "
            "o inicia sesión con tu código corporativo."
        )
        st.stop()

    with st.spinner("Procesando Carpeta Tributaria en memoria RAM..."):
        try:
            result, json_bytes, markdown_bytes = process_pdf(
                uploaded_file, cupo_solicitado=cupo_solicitado or None
            )
            st.session_state["result"] = result
            st.session_state["json_bytes"] = json_bytes
            st.session_state["markdown_bytes"] = markdown_bytes

            # Descontar crédito únicamente si es una carpeta distinta
            if access_tier == "FREE_TRIAL" and is_distinct_file:
                st.session_state.setdefault("evaluated_fingerprints", []).append(file_fp)
                st.session_state["free_credits_remaining"] = max(0, free_credits - 1)
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

    # Aviso si consumió sus 2 créditos gratis
    if (
        access_tier == "FREE_TRIAL"
        and st.session_state.get("free_credits_remaining", 0) == 0
    ):
        st.warning(
            "🎁 **Has utilizado tus 2 evaluaciones gratuitas.** Puedes seguir consultando, exportando "
            "y re-evaluando las carpetas de esta sesión. Para evaluar carpetas adicionales, contáctanos en "
            "**contacto@cavilaria.com** para activar tu cuenta corporativa ilimitada."
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
        show_export(result, auth_role=access_tier)

    st.divider()
    show_downloads(result)
