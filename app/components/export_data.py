import json
import streamlit as st

from app.utils.exporter import generate_csv, generate_excel
from app.utils.formatting import fmt_currency
from src.credit.sector_benchmark import SectorBenchmark
from src.models.tax_folder import TaxFolder
from src.reports.excel_report import ExcelReport
from src.reports.pdf_report import PDFReport


def show_export(tax_folder: TaxFolder, auth_role: str = "client") -> None:
    st.subheader("Informes y Exportaciones de Datos")

    # Descargas Ejecutivas Oficiales
    col_rep1, col_rep2 = st.columns(2)
    rut_val = getattr(getattr(tax_folder, "contributor", None), "rut", "empresa") or "empresa"
    rut_clean = str(rut_val).replace(".", "").replace("-", "").strip()

    with col_rep1:
        st.markdown("**Dictamen Oficial de Comité (PDF)**")
        st.caption("Documento formal con veredicto, cupo en M$, memoria de cálculo y sellos.")
        try:
            pdf_bytes = PDFReport().generate(tax_folder)
            st.download_button(
                label="📄 Descargar Dictamen Ejecutivo (PDF)",
                data=pdf_bytes,
                file_name=f"dictamen_comite_{rut_clean}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="btn_export_pdf",
            )
        except Exception as e:
            st.error(f"Error generando PDF: {e}")

    with col_rep2:
        st.markdown("**Cartola Completa y Dictamen (Excel)**")
        st.caption("Libro Excel con 4 pestañas: Dictamen, Flujos F29, Patrimonio F22 y Ficha Socios.")
        try:
            excel_bytes = ExcelReport().generate(tax_folder)
            st.download_button(
                label="📊 Descargar Cartola y Dictamen (Excel .xlsx)",
                data=excel_bytes,
                file_name=f"cartola_dictamen_{rut_clean}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="btn_export_excel",
            )
        except Exception as e:
            st.error(f"Error generando Excel: {e}")

    st.divider()
    st.subheader("Exportación Personalizada de Ventas y Compras")
    if not tax_folder.monthly_taxes:
        st.info("No hay datos mensuales para exportar.")
        return

    periodos = sorted(
        [mt.periodo for mt in tax_folder.monthly_taxes],
        key=lambda x: x,
    )
    desde = st.selectbox("Fecha desde", periodos, index=0, key="export_desde")
    hasta = st.selectbox("Fecha hasta", periodos, index=len(periodos) - 1, key="export_hasta")

    formato = st.radio("Formato", ["Excel (.xlsx)", "CSV"], horizontal=True)

    if st.button("Descargar", type="primary"):
        if desde > hasta:
            st.error("La fecha 'desde' debe ser anterior o igual a 'hasta'.")
            return

        if formato == "Excel (.xlsx)":
            data = generate_excel(tax_folder.monthly_taxes, desde, hasta)
            if not data:
                st.warning("No hay datos en el período seleccionado.")
                return
            st.download_button(
                label="Descargar Excel",
                data=data,
                file_name=f"ventas_compras_{desde}_{hasta}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            data = generate_csv(tax_folder.monthly_taxes, desde, hasta)
            if not data:
                st.warning("No hay datos en el período seleccionado.")
                return
            st.download_button(
                label="Descargar CSV",
                data=data,
                file_name=f"ventas_compras_{desde}_{hasta}.csv",
                mime="text/csv",
            )

    # Funciones exclusivas para Administradores
    if str(auth_role).upper() == "ADMIN":
        st.divider()
        st.subheader("Administración: Telemetría y Prospectos Registrados")

        col_admin1, col_admin2 = st.columns(2)
        with col_admin1:
            st.markdown("**Benchmark Sectorial Anónimo**")
            st.caption("Ratios agregados por giro SII (sin PII ni huellas privadas).")
            bench = SectorBenchmark()
            bench_data = json.dumps(
                bench.get_all(include_private=False), indent=2, ensure_ascii=False
            ).encode("utf-8")
            st.download_button(
                label="📊 Descargar Benchmark Sectorial (JSON)",
                data=bench_data,
                file_name="sector_benchmarks.json",
                mime="application/json",
                key="btn_download_benchmark",
            )

        with col_admin2:
            st.markdown("**Prospectos Registrados (Leads)**")
            st.caption("Contactos que activaron evaluaciones gratuitas de prueba.")
            from src.leads.lead_manager import LeadManager

            lm = LeadManager()
            leads_csv = lm.exportar_csv()
            st.download_button(
                label="👥 Descargar Prospectos Registrados (CSV)",
                data=leads_csv,
                file_name="leads_registrados.csv",
                mime="text/csv",
                key="btn_download_leads_csv",
            )

