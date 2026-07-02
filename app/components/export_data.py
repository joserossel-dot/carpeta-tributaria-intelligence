import streamlit as st

from app.utils.exporter import generate_csv, generate_excel
from app.utils.formatting import fmt_currency
from src.models.tax_folder import TaxFolder


def show_export(tax_folder: TaxFolder) -> None:
    st.subheader("Exportar Ventas y Compras")
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
