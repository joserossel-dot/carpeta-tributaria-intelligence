"""Test de regresión de consistencia interna v2.9.1 para los 4 casos benchmark."""
from decimal import Decimal
import io
from pathlib import Path
import pdfplumber
import pytest

from src.core.tax_folder_engine import TaxFolderEngine
from src.reports.pdf_report import PDFReport, format_mclp

BENCHMARK_CASES = [
    {
        "name": "ALVAL SPA",
        "rut": "76293939-8",
        "path": Path("/Users/josealfonsorossel/Downloads/Carpeta_Tributaria_Regular (8).pdf"),
        "has_debito": True,
    },
    {
        "name": "NUTRISA",
        "rut": "95214000-0",
        "path": Path("/Users/josealfonsorossel/Downloads/Carpeta Tributaria Personalizada NUTRISA.pdf"),
        "has_debito": True,
    },
    {
        "name": "PROTERM S.A.",
        "rut": "78155540-1",
        "path": Path("/Users/josealfonsorossel/Downloads/Carpeta_Tributaria_Regular (4).pdf"),
        "has_debito": True,
    },
    {
        "name": "CLINICA HYPERBARIC SPA",
        "rut": "77460385-9",
        "path": (
            Path("/Users/josealfonsorossel/Downloads/Carpeta Tributaria.CLINICA HYPERBARIC.pdf")
            if Path("/Users/josealfonsorossel/Downloads/Carpeta Tributaria.CLINICA HYPERBARIC.pdf").exists()
            else Path("examples/Carpeta Tributaria.CLINICA HYPERBARIC.pdf")
        ),
        "has_debito": False,
    },
]


@pytest.mark.parametrize("case", BENCHMARK_CASES, ids=lambda c: c["name"])
def test_pdf_internal_consistency(case):
    """Verifica mandatos de consistencia interna v2.9.1 en cada caso benchmark."""
    if not case["path"].exists():
        pytest.skip(f"Archivo de prueba {case['path']} no disponible")

    engine = TaxFolderEngine(str(case["path"]))
    folder = engine.parse()
    assert folder.credit_risk is not None

    last_12 = folder.monthly_taxes[-12:]
    assert len(last_12) == 12

    # Totales brutos y en M$ de la tabla F29
    tot_deb = sum(m.debito_fiscal or Decimal("0") for m in last_12)
    tot_cred = sum(
        (m.credito_operacional if m.credito_operacional is not None else (m.credito_fiscal or Decimal("0")))
        for m in last_12
    )
    tot_cop = sum(
        (m.compras_operacionales if m.compras_operacionales is not None else (m.compras or Decimal("0")))
        for m in last_12
    )
    tot_iva = sum(m.iva_determinado or Decimal("0") for m in last_12)

    tot_deb_m = round(float(tot_deb) / 1000.0)
    tot_cred_m = round(float(tot_cred) / 1000.0)
    tot_cop_m = round(float(tot_cop) / 1000.0)

    tot_v = sum(m.total_ventas or Decimal("0") for m in last_12)
    ratio_cop_v = float(tot_cop) / float(tot_v) if tot_v > 0 else 0.0
    es_servicios = (ratio_cop_v < 0.35 and tot_v > 0)

    # 1. Mandato a: Ratio Pilar 3
    pilar3 = next(
        p for p in folder.credit_risk.desglose_score
        if "Débito" in p.nombre or "Holgura" in p.nombre
    )
    if es_servicios:
        assert pilar3.puntaje_obtenido == 12
        assert "Estructura de Servicios (Compras representan <35% de ventas)" in pilar3.detalle
    elif case["has_debito"]:
        ratio_dc = round(tot_deb_m / tot_cred_m, 2)
        ratio_str = f"{ratio_dc:.2f}x"
        assert ratio_str in pilar3.detalle, (
            f"En {case['name']}, ratio {ratio_str} no encontrado en Pilar 3 detalle: '{pilar3.detalle}'"
        )
    else:
        assert "Giro exento de IVA (Débito 12M: M$ 0)" in pilar3.detalle

    # 2. Mandato b: Débito Fiscal - Crédito Giro Mes == IVA Determinado (sin arrastre de remanente previo)
    for m in last_12:
        rem_ant = getattr(m, "remanente_anterior", None) or getattr(m, "remanente_credito_mes_anterior", None) or Decimal("0")
        if rem_ant == 0:
            deb = m.debito_fiscal or Decimal("0")
            cred_giro = m.credito_operacional if m.credito_operacional is not None else (m.credito_fiscal or Decimal("0"))
            iva_det = m.iva_determinado or Decimal("0")
            # En períodos con débito > crédito y sin remanente anterior, deb - cred debe ser igual al IVA determinado
            if deb >= cred_giro:
                assert deb - cred_giro == iva_det, (
                    f"Descuadre IVA en {case['name']} período {m.periodo}: "
                    f"Débito {deb} - Crédito {cred_giro} != IVA Determinado {iva_det}"
                )

    # 3. Mandato c: Promedio_Compras == round(Tabla_Total_Compras / 12)
    prom_cop_m = round(tot_cop_m / 12)
    prom_cop_directo = round(float(tot_cop / Decimal("12")) / 1000.0)
    # Deben coincidir exactamente dentro del redondeo de M$
    assert abs(prom_cop_m - prom_cop_directo) <= 1

    # 4. Mandato d: Si se imprime un ratio X.XX, el texto final del PDF debe contener exactamente ese X.XX
    pdf_bytes = PDFReport().generate(folder)
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        full_text = " ".join(" ".join(p.extract_text().split()) for p in pdf.pages)
        if es_servicios:
            assert "Estructura de Servicios" in full_text
        elif case["has_debito"]:
            ratio_dc = round(tot_deb_m / tot_cred_m, 2)
            ratio_str = f"{ratio_dc:.2f}x"
            assert ratio_str in full_text, (
                f"El PDF generado para {case['name']} no contiene el ratio esperado {ratio_str}"
            )
        # Verificar que el promedio de compras de la tabla esté presente
        prom_cop_str = format_mclp(tot_cop / Decimal("12"))
        assert prom_cop_str in full_text, (
            f"El PDF generado para {case['name']} no contiene el promedio mensual de compras {prom_cop_str}"
        )
