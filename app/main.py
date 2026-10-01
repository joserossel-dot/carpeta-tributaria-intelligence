import gc
import hashlib
import json
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
from src.credit.sector_benchmark import SectorBenchmark
from src.leads.lead_manager import LeadManager, validar_email

# 1. Configuración de Marca Blanca y Paginación
st.set_page_config(
    page_title="Cavilaria | Evaluación Tributaria y Crédito B2B",
    page_icon="🏢",
    layout="wide",
)

# 2. Inyección CSS Corporativo Cavilaria (Color base #F26822) e incrustación Iframe
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

    /* Pestañas (Tabs) Corporativas Cavilaria */
    div[data-testid="stTabs"] button {
        color: #F26822 !important;
        font-weight: bold !important;
        font-size: 1.1rem !important;
    }
    div[data-testid="stTabs"] button p,
    div[data-testid="stTabs"] button div,
    div[data-testid="stTabs"] button span {
        color: #F26822 !important;
        font-weight: bold !important;
        font-size: 1.1rem !important;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #F26822 !important;
        font-weight: bold !important;
        border-bottom-color: #F26822 !important;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        background-color: #F26822 !important;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-border"] {
        border-bottom-color: #F26822 !important;
    }

    /* Botones Corporativos Cavilaria (stButton, stDownloadButton, stFormSubmitButton) */
    div[data-testid="stButton"] > button,
    div[data-testid="stDownloadButton"] > button,
    div[data-testid="stFormSubmitButton"] > button,
    .stButton > button,
    .stDownloadButton > button,
    .stFormSubmitButton > button {
        background-color: #F26822 !important;
        color: #FFFFFF !important;
        border: 2px solid #F26822 !important;
        font-weight: bold !important;
        border-radius: 6px !important;
        transition: all 0.2s ease-in-out !important;
    }

    div[data-testid="stButton"] > button p,
    div[data-testid="stDownloadButton"] > button p,
    div[data-testid="stFormSubmitButton"] > button p,
    .stButton > button p,
    .stDownloadButton > button p,
    .stFormSubmitButton > button p {
        color: #FFFFFF !important;
        font-weight: bold !important;
    }

    div[data-testid="stButton"] > button:hover,
    div[data-testid="stDownloadButton"] > button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover,
    .stButton > button:hover,
    .stDownloadButton > button:hover,
    .stFormSubmitButton > button:hover {
        background-color: #FFFFFF !important;
        color: #F26822 !important;
        border: 2px solid #F26822 !important;
    }

    div[data-testid="stButton"] > button:hover p,
    div[data-testid="stDownloadButton"] > button:hover p,
    div[data-testid="stFormSubmitButton"] > button:hover p,
    .stButton > button:hover p,
    .stDownloadButton > button:hover p,
    .stFormSubmitButton > button:hover p {
        color: #F26822 !important;
    }

    div[data-testid="stButton"] > button:focus,
    div[data-testid="stDownloadButton"] > button:focus,
    div[data-testid="stFormSubmitButton"] > button:focus,
    .stButton > button:focus,
    .stDownloadButton > button:focus,
    .stFormSubmitButton > button:focus {
        border-color: #F26822 !important;
        box-shadow: 0 0 0 0.2rem rgba(242, 104, 34, 0.25) !important;
    }

    div[data-testid="stButton"] > button:disabled,
    div[data-testid="stDownloadButton"] > button:disabled,
    div[data-testid="stFormSubmitButton"] > button:disabled,
    .stButton > button:disabled,
    .stDownloadButton > button:disabled,
    .stFormSubmitButton > button:disabled {
        background-color: #FDBA74 !important;
        color: #FFFFFF !important;
        border-color: #FDBA74 !important;
        opacity: 0.65 !important;
        cursor: not-allowed !important;
    }

    div[data-testid="stButton"] > button:disabled:hover,
    div[data-testid="stDownloadButton"] > button:disabled:hover,
    div[data-testid="stFormSubmitButton"] > button:disabled:hover,
    .stButton > button:disabled:hover,
    .stDownloadButton > button:disabled:hover,
    .stFormSubmitButton > button:disabled:hover {
        background-color: #FDBA74 !important;
        color: #FFFFFF !important;
        border-color: #FDBA74 !important;
    }

    div[data-testid="stButton"] > button:disabled:hover p,
    div[data-testid="stDownloadButton"] > button:disabled:hover p,
    div[data-testid="stFormSubmitButton"] > button:disabled:hover p,
    .stButton > button:disabled:hover p,
    .stDownloadButton > button:disabled:hover p,
    .stFormSubmitButton > button:disabled:hover p {
        color: #FFFFFF !important;
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

# Restauración automática de sesión desde st.query_params (anti-expulsión en iframe cross-domain)
if not st.session_state.get("authenticated", False):
    param_code = str(st.query_params.get("access_code", "")).strip()
    if param_code:
        if param_code == ADMIN_CODE:
            st.session_state["authenticated"] = True
            st.session_state["access_tier"] = "ADMIN"
            st.session_state["access_code"] = ADMIN_CODE
            st.session_state["free_credits_remaining"] = 999999
            st.session_state["evaluated_fps"] = set()
            st.session_state["evaluated_fingerprints"] = []
        elif param_code == CLIENT_CODE:
            st.session_state["authenticated"] = True
            st.session_state["access_tier"] = "CLIENT"
            st.session_state["access_code"] = CLIENT_CODE
            st.session_state["free_credits_remaining"] = 999999
            st.session_state["evaluated_fps"] = set()
            st.session_state["evaluated_fingerprints"] = []
        elif param_code.startswith("FREE-") or param_code.startswith("FREE_"):
            lead_id_or_hash = param_code.split("-", 1)[-1] if "-" in param_code else param_code.split("_", 1)[-1]
            lm = LeadManager()
            lead_found = lm.obtener_lead_por_id_o_email(lead_id_or_hash)
            if lead_found:
                evals = lead_found.get("evaluaciones_realizadas", 0)
                credits_left = max(0, 2 - evals)
                st.session_state["authenticated"] = True
                st.session_state["access_tier"] = "FREE_TRIAL"
                st.session_state["access_code"] = param_code
                st.session_state["free_credits_remaining"] = credits_left
                st.session_state["evaluated_fps"] = set()
                st.session_state["evaluated_fingerprints"] = []
                st.session_state["user_info"] = {
                    "nombre": lead_found.get("nombre", ""),
                    "empresa": lead_found.get("empresa", ""),
                    "email": lead_found.get("email", ""),
                }
            else:
                st.session_state["authenticated"] = True
                st.session_state["access_tier"] = "FREE_TRIAL"
                st.session_state["access_code"] = param_code
                st.session_state["free_credits_remaining"] = 2
                st.session_state["evaluated_fps"] = set()
                st.session_state["evaluated_fingerprints"] = []

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

            # Casillas de Consentimiento (Ley N° 21.719)
            acepto_privacidad = st.checkbox(
                "He leído y acepto la [Política de Privacidad (v1.1)](https://cavilaria.com/politica-de-privacidad) de Cavilaria SpA para el tratamiento de mis datos de contacto.",
                value=False,
            )
            acepto_comercial = st.checkbox(
                "Acepto recibir comunicaciones comerciales, seguimiento de mi evaluación y novedades de Cavilaria SpA.",
                value=False,
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
                elif not acepto_privacidad:
                    st.error("Debes aceptar la Política de Privacidad para continuar.")
                else:
                    lead_rec = None
                    try:
                        lm = LeadManager()
                        lead_rec = lm.registrar_lead(
                            nombre=nombre,
                            empresa=empresa,
                            email=email,
                            telefono=telefono,
                            privacy_opt_in=acepto_privacidad,
                            marketing_opt_in=acepto_comercial,
                            policy_version="v1.1",
                        )
                    except Exception:
                        pass

                    lead_id = lead_rec.id if lead_rec else hashlib.sha256(email.strip().lower().encode()).hexdigest()[:12]
                    free_token = f"FREE-{lead_id}"

                    st.session_state["authenticated"] = True
                    st.session_state["access_tier"] = "FREE_TRIAL"
                    st.session_state["access_code"] = free_token
                    st.session_state["free_credits_remaining"] = 2
                    st.session_state["evaluated_fps"] = set()
                    st.session_state["evaluated_fingerprints"] = []
                    st.session_state["user_info"] = {
                        "nombre": nombre.strip(),
                        "empresa": empresa.strip(),
                        "email": email.strip().lower(),
                    }
                    st.query_params["access_code"] = free_token
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
                    st.session_state["access_code"] = ADMIN_CODE
                    st.session_state["free_credits_remaining"] = 999999
                    st.session_state["evaluated_fps"] = set()
                    st.session_state["evaluated_fingerprints"] = []
                    st.query_params["access_code"] = ADMIN_CODE
                    st.rerun()
                elif clean_code == CLIENT_CODE:
                    st.session_state["authenticated"] = True
                    st.session_state["access_tier"] = "CLIENT"
                    st.session_state["access_code"] = CLIENT_CODE
                    st.session_state["free_credits_remaining"] = 999999
                    st.session_state["evaluated_fps"] = set()
                    st.session_state["evaluated_fingerprints"] = []
                    st.query_params["access_code"] = CLIENT_CODE
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
        if "access_code" in st.query_params:
            del st.query_params["access_code"]
        st.session_state.clear()
        gc.collect()
        st.rerun()

# Panel de Control Administrador (Visible de inmediato para Socios/Admin sin requerir PDF)
if access_tier == "ADMIN":
    with st.expander("🛠️ Panel de Control Administrador — Prospectos Inscritos y Benchmark (Solo Socios)", expanded=False):
        lm = LeadManager()
        leads = lm.obtener_leads()
        total_leads = len(leads)
        optin_marketing = sum(1 for l in leads if l.get("marketing_opt_in") is True)

        col_adm_m1, col_adm_m2 = st.columns(2)
        with col_adm_m1:
            st.metric("Total Prospectos Registrados", total_leads)
        with col_adm_m2:
            st.metric("Con Opt-In Comercial Activo", optin_marketing)

        st.markdown("##### Listado de Prospectos en Vivo")
        if leads:
            st.dataframe(leads, use_container_width=True)
        else:
            st.info("Aún no se han registrado prospectos.")

        st.markdown("##### Descargas de Gestión")
        col_adm_dl1, col_adm_dl2 = st.columns(2)
        with col_adm_dl1:
            leads_csv = lm.exportar_csv()
            st.download_button(
                label="👥 Descargar Prospectos Registrados (CSV Excel)",
                data=leads_csv,
                file_name="leads_registrados.csv",
                mime="text/csv",
                key="btn_admin_leads_csv",
                use_container_width=True,
            )
        with col_adm_dl2:
            bench = SectorBenchmark()
            bench_data = json.dumps(
                bench.get_all(include_private=False), indent=2, ensure_ascii=False
            ).encode("utf-8")
            st.download_button(
                label="📊 Descargar Benchmark Sectorial (JSON)",
                data=bench_data,
                file_name="sector_benchmarks.json",
                mime="application/json",
                key="btn_admin_benchmark_json",
                use_container_width=True,
            )

st.divider()

# 5. Entrada de Documento y Cupo Solicitado
uploaded_file = st.file_uploader(
    "Arrastra la Carpeta Tributaria PDF aquí",
    type=["pdf"],
    accept_multiple_files=False,
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

col_com1, col_com2 = st.columns(2)
with col_com1:
    boletin_comercial = st.selectbox(
        "Boletín Comercial (Dicom/Equifax)",
        [
            "Pendiente de consulta (Condiciona línea)",
            "Verificado: Sin morosidad ni protestos",
            "Verificado: Con morosidad vigente",
        ],
        index=0,
        help="Evaluación del comportamiento crediticio externo. Si registra morosidad vigente, la recomendación se restringe a M$ 0 (Contado).",
    )
with col_com2:
    historial_pago = st.selectbox(
        "Historial de Pago con Proveedor",
        [
            "Cliente nuevo (Sin historial previo)",
            "Cliente con historial de pago oportuno",
            "Cliente con atrasos previos",
        ],
        index=0,
        help="Para clientes nuevos o con alertas aplica la Línea Inicial de Apertura (50% del techo técnico).",
    )

col1, col2, col3, col4 = st.columns(4)
with col1:
    analizar = st.button("Analizar", type="primary", disabled=uploaded_file is None, use_container_width=True)
with col2:
    if st.button("Limpiar", use_container_width=True):
        tier = st.session_state.get("access_tier")
        credits = st.session_state.get("free_credits_remaining")
        raw_fps = st.session_state.get("evaluated_fps")
        if raw_fps is None:
            raw_fps = st.session_state.get("evaluated_fingerprints")
        if not isinstance(raw_fps, (set, list, tuple)):
            fps_set = set()
        else:
            fps_set = set(str(x) for x in raw_fps if x is not None)
        uinfo = st.session_state.get("user_info")
        code = st.session_state.get("access_code")

        st.session_state.clear()

        st.session_state["authenticated"] = True
        st.session_state["access_tier"] = tier
        st.session_state["free_credits_remaining"] = credits
        st.session_state["evaluated_fps"] = fps_set
        st.session_state["evaluated_fingerprints"] = list(fps_set)
        st.session_state["user_info"] = uinfo
        if code:
            st.session_state["access_code"] = code
            st.query_params["access_code"] = code
        gc.collect()
        st.rerun()

ph_pdf_arriba = col3.empty()
ph_excel_arriba = col4.empty()

# 6. Ejecución del Análisis y Control de Créditos
if uploaded_file is not None and analizar:
    file_bytes = uploaded_file.getvalue()
    # Huella criptográfica rápida del archivo para no descontar créditos si solo cambia el cupo solicitado
    file_fp = hashlib.sha256(file_bytes[:4096] + str(len(file_bytes)).encode()).hexdigest()[:16]
    raw_fps = st.session_state.get("evaluated_fps")
    if raw_fps is None:
        raw_fps = st.session_state.get("evaluated_fingerprints")
    if not isinstance(raw_fps, (set, list, tuple)):
        evaluated_fps = set()
    else:
        evaluated_fps = set(str(x) for x in raw_fps if x is not None)
    st.session_state["evaluated_fps"] = evaluated_fps
    st.session_state["evaluated_fingerprints"] = list(evaluated_fps)
    file_fp = str(file_fp) if file_fp is not None else ""
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
                uploaded_file,
                cupo_solicitado=cupo_solicitado or None,
                boletin_comercial=boletin_comercial,
                historial_pago=historial_pago,
            )
            st.session_state["result"] = result
            st.session_state["json_bytes"] = json_bytes
            st.session_state["markdown_bytes"] = markdown_bytes

            # Descontar crédito únicamente si es una carpeta distinta
            if access_tier == "FREE_TRIAL" and is_distinct_file:
                evaluated_fps.add(file_fp)
                st.session_state["evaluated_fps"] = evaluated_fps
                st.session_state["evaluated_fingerprints"] = list(evaluated_fps)
                st.session_state["free_credits_remaining"] = max(0, free_credits - 1)

                acc_code = st.session_state.get("access_code", "")
                lead_target = acc_code[5:] if acc_code.startswith("FREE-") else (
                    st.session_state.get("user_info", {}).get("email")
                )
                if lead_target:
                    try:
                        lm = LeadManager()
                        lm.incrementar_evaluaciones(lead_target)
                    except Exception:
                        pass
        except Exception as e:
            st.error(f"Error al procesar el PDF: {e}")
            st.stop()

if "result" in st.session_state:
    result = st.session_state["result"]
    json_bytes = st.session_state["json_bytes"]
    markdown_bytes = st.session_state["markdown_bytes"]

    # Generación y caché en memoria de informes PDF y Excel
    rut_val = getattr(getattr(result, "contributor", None), "rut", "empresa") or "empresa"
    rut_clean = str(rut_val).replace(".", "").replace("-", "").strip()

    if "cached_pdf_data" not in st.session_state or st.session_state.get("cached_download_rut") != rut_clean:
        from src.reports.excel_report import ExcelReport
        from src.reports.pdf_report import PDFReport
        st.session_state["cached_pdf_data"] = PDFReport().generate(result)
        st.session_state["cached_excel_data"] = ExcelReport().generate(result)
        st.session_state["cached_download_rut"] = rut_clean
        gc.collect()

    pdf_data = st.session_state["cached_pdf_data"]
    excel_data = st.session_state["cached_excel_data"]

    # Inyección en placeholders de la botonera superior (col3 y col4)
    ph_pdf_arriba.download_button(
        label="Descargar PDF",
        data=pdf_data,
        file_name=f"evaluacion_tributaria_{rut_clean}.pdf",
        mime="application/pdf",
        key="pdf_arriba",
        use_container_width=True,
    )
    ph_excel_arriba.download_button(
        label="Descargar Excel",
        data=excel_data,
        file_name=f"cartola_evaluacion_{rut_clean}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="excel_arriba",
        use_container_width=True,
    )

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

    # 4. Réplica de botonera de descarga inferior
    st.markdown("---")
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(
            label="Descargar PDF",
            data=pdf_data,
            file_name=f"evaluacion_tributaria_{rut_clean}.pdf",
            mime="application/pdf",
            key="pdf_abajo",
            use_container_width=True,
        )
    with col_dl2:
        st.download_button(
            label="Descargar Excel",
            data=excel_data,
            file_name=f"cartola_evaluacion_{rut_clean}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="excel_abajo",
            use_container_width=True,
        )
