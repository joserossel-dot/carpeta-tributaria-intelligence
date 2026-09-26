"""Módulo de Telemetría Estadística Anónima (Zero-PII).

Captura únicamente ratios financieros normalizados y agregados por código de
actividad económica (Giro SII). No almacena RUTs, razones sociales, socios,
representantes, domicilios ni documentos originales.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.models.tax_folder import TaxFolder


def clasificar_tramo_ventas(ventas_12m: float) -> str:
    """Clasifica el tramo de facturación anual en segmentos comerciales."""
    if ventas_12m < 100_000_000:
        return "< 100M"
    elif ventas_12m < 500_000_000:
        return "100M - 500M"
    elif ventas_12m < 2_000_000_000:
        return "500M - 2.000M"
    elif ventas_12m < 10_000_000_000:
        return "2.000M - 10.000M"
    else:
        return "> 10.000M"


class AnonymousBenchmarkRecord(BaseModel):
    """Registro anónimo de telemetría estadística sectorial.

    Garantiza Zero-PII:
    - Código de actividad SII numérico.
    - Tramo de ventas categórico.
    - Ratios financieros normalizados (sin cifras crudas identificables).
    - Huella hash SHA-256 truncada a 16 caracteres para deduplicación.
    """

    codigo_actividad: str = Field(..., description="Código de actividad económica SII (giro)")
    tramo_ventas_anuales: str = Field(..., description="Rango de ventas anuales")
    ratio_compras_ventas: float = Field(..., description="Compras 12m / Ventas 12m")
    margen_bruto_proxy: float = Field(..., description="Margen proxy (Ventas - Compras) / Ventas")
    ratio_debito_credito: float | None = Field(None, description="Ratio Débito Fiscal / Crédito Fiscal")
    variacion_ventas_yoy: float | None = Field(None, description="Variación interanual de ventas (%)")
    ratio_cpt_ventas: float | None = Field(None, description="Capital Propio Tributario / Ventas 12M")
    ratio_cupo_recomendado_ventas: float | None = Field(None, description="Cupo sugerido / Ventas 12M")
    timestamp: str = Field(..., description="Timestamp ISO 8601 UTC de la captura")
    fingerprint: str = Field(..., description="Hash SHA-256 anonimizado de 16 caracteres para deduplicación")


def generar_fingerprint(
    codigo_actividad: str,
    ultimo_f29: str,
    ventas_12m: float,
    compras_12m: float,
) -> str:
    """Genera una huella criptográfica anónima unidireccional de 16 caracteres.

    Utiliza magnitudes normalizadas y el período tributario.
    Jamás incluye RUT ni identificadores personales.
    """
    raw = f"{codigo_actividad}|{ultimo_f29}|{round(ventas_12m, -4)}|{round(compras_12m, -4)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def extraer_registro_anonimo(tax_folder: TaxFolder) -> AnonymousBenchmarkRecord | None:
    """Extrae un registro de telemetría 100% anónimo a partir de una carpeta tributaria.

    Si faltan ventas o código de actividad, retorna None.
    Valida estrictamente que ningún dato de PII (RUT o nombres) se filtre en el payload.
    """
    # 1. Código de actividad
    codigo_actividad = None
    if tax_folder.activities:
        for act in tax_folder.activities:
            if act.principal:
                codigo_actividad = str(act.codigo).strip()
                break
        if not codigo_actividad and tax_folder.activities:
            codigo_actividad = str(tax_folder.activities[0].codigo).strip()

    if not codigo_actividad:
        return None

    # 2. Ventas y costos 12M con corrección de costos operativos y giros exentos/exportadores
    ventas_12m = 0.0
    last_12 = tax_folder.monthly_taxes[-12:] if tax_folder.monthly_taxes else []
    n_meses = len(last_12) if last_12 else 12

    if tax_folder.monthly_analysis and tax_folder.monthly_analysis.ventas_ultimos_12 is not None:
        ventas_12m = float(tax_folder.monthly_analysis.ventas_ultimos_12)
    elif last_12:
        ventas_12m = float(sum(mt.total_ventas for mt in last_12 if mt.total_ventas))

    if ventas_12m <= 0:
        return None

    # Compras operacionales 12M
    if (
        tax_folder.monthly_analysis
        and tax_folder.monthly_analysis.promedio_compras_operacionales_12m is not None
    ):
        compras_op_12m = float(tax_folder.monthly_analysis.promedio_compras_operacionales_12m) * n_meses
    elif last_12:
        compras_op_12m = float(
            sum(
                (mt.compras_operacionales if mt.compras_operacionales is not None else (mt.compras or 0))
                for mt in last_12
            )
        )
    else:
        compras_op_12m = 0.0

    # Costo operativo proxy 12M (Honorarios / 0.1375 + Sueldos * 15, con piso de 30% de ventas)
    if (
        tax_folder.monthly_analysis
        and tax_folder.monthly_analysis.promedio_costo_operativo_proxy_12m is not None
    ):
        costo_proxy_12m = float(tax_folder.monthly_analysis.promedio_costo_operativo_proxy_12m) * n_meses
    elif last_12:
        costos_m = []
        for mt in last_12:
            cop = float(mt.compras_operacionales if mt.compras_operacionales is not None else (mt.compras or 0))
            hon = (float(mt.retencion_honorarios) / 0.1375) if (mt.retencion_honorarios and mt.retencion_honorarios > 0) else 0.0
            sue = (float(mt.retencion_sueldos) * 15.0) if (mt.retencion_sueldos and mt.retencion_sueldos > 0) else 0.0
            costos_m.append(cop + hon + sue)
        prom_c = sum(costos_m) / len(last_12) if last_12 else 0.0
        prom_v = ventas_12m / len(last_12) if last_12 else 0.0
        costo_proxy_12m = max(prom_c, prom_v * 0.30) * len(last_12)
    else:
        costo_proxy_12m = ventas_12m * 0.30

    # Costo operativo total: máximo entre compras operacionales y proxy de costo
    costo_operativo_total_12m = max(compras_op_12m, costo_proxy_12m)
    if costo_operativo_total_12m <= 0:
        compras_fallback = float(tax_folder.monthly_analysis.compras_ultimos_12 or 0) if tax_folder.monthly_analysis else 0.0
        costo_operativo_total_12m = max(compras_fallback, ventas_12m * 0.30)

    tramo = clasificar_tramo_ventas(ventas_12m)
    ratio_cv = round(costo_operativo_total_12m / ventas_12m, 4)
    margen_proxy = round(max(-2.0, min(1.0, (ventas_12m - costo_operativo_total_12m) / ventas_12m)), 4)

    # Identificar empresas exportadoras o con ventas exentas > 20%
    ventas_exentas_12m = sum(float(mt.ventas_exentas or 0) for mt in last_12)
    ventas_export_12m = sum(float(mt.ventas_exportacion or 0) for mt in last_12)
    pct_no_afectas = (ventas_exentas_12m + ventas_export_12m) / ventas_12m if ventas_12m > 0 else 0.0

    if pct_no_afectas > 0.20:
        # En empresas exportadoras o exentas, el Débito Fiscal IVA está distorsionado (Cód. 020 no genera Cód. 538).
        # Se utiliza el ratio operacional equivalente: Ventas 12M / Costo Operativo Total 12M
        ratio_dc = round(ventas_12m / costo_operativo_total_12m, 4) if costo_operativo_total_12m > 0 else 1.0
    else:
        ratio_dc = None
        if (
            tax_folder.credit_risk
            and hasattr(tax_folder.credit_risk, "indicadores")
            and tax_folder.credit_risk.indicadores.margen_vs_giro.ratio_debito_credito_12m
            and tax_folder.credit_risk.indicadores.margen_vs_giro.ratio_debito_credito_12m > 0
        ):
            ratio_dc = round(
                float(tax_folder.credit_risk.indicadores.margen_vs_giro.ratio_debito_credito_12m), 4
            )
        if ratio_dc is None:
            ratio_dc = round(ventas_12m / costo_operativo_total_12m, 4) if costo_operativo_total_12m > 0 else 1.0

    # Variación YoY de ventas
    var_yoy = None
    if tax_folder.monthly_analysis:
        if tax_folder.monthly_analysis.variacion_ventas_yoy_3m_pct is not None:
            var_yoy = round(float(tax_folder.monthly_analysis.variacion_ventas_yoy_3m_pct), 2)
        elif tax_folder.monthly_analysis.crecimiento_anual is not None:
            var_yoy = round(float(tax_folder.monthly_analysis.crecimiento_anual), 2)

    # Ratio CPT / Ventas
    ratio_cpt = None
    cpt = None
    if (
        tax_folder.credit_risk
        and hasattr(tax_folder.credit_risk, "indicadores")
        and tax_folder.credit_risk.indicadores.respaldo_estructural.capital_propio_tributario
    ):
        cpt = float(
            tax_folder.credit_risk.indicadores.respaldo_estructural.capital_propio_tributario
        )
    elif tax_folder.f22:
        for f in reversed(tax_folder.f22):
            if f.capital_propio_tributario and f.capital_propio_tributario > 0:
                cpt = float(f.capital_propio_tributario)
                break

    if cpt and cpt > 0:
        ratio_cpt = round(cpt / ventas_12m, 4)

    # Ratio Cupo / Ventas
    ratio_cupo = None
    if tax_folder.credit_risk:
        cupo = tax_folder.credit_risk.cupo_aprobado or tax_folder.credit_risk.cupo_maximo_sugerido
        if cupo and cupo > 0:
            ratio_cupo = round(float(cupo) / ventas_12m, 4)

    # Último período F29
    ultimo_f29 = ""
    if tax_folder.monthly_taxes:
        ultimo_f29 = tax_folder.monthly_taxes[-1].periodo
    elif tax_folder.f29:
        ultimo_f29 = tax_folder.f29[-1].periodo

    fingerprint = generar_fingerprint(codigo_actividad, ultimo_f29, ventas_12m, costo_operativo_total_12m)
    timestamp = datetime.now(timezone.utc).isoformat()

    record = AnonymousBenchmarkRecord(
        codigo_actividad=codigo_actividad,
        tramo_ventas_anuales=tramo,
        ratio_compras_ventas=ratio_cv,
        margen_bruto_proxy=margen_proxy,
        ratio_debito_credito=ratio_dc,
        variacion_ventas_yoy=var_yoy,
        ratio_cpt_ventas=ratio_cpt,
        ratio_cupo_recomendado_ventas=ratio_cupo,
        timestamp=timestamp,
        fingerprint=fingerprint,
    )

    # Verificación de privacidad: asegurarse de que NINGÚN dato PII esté en el record
    record_json = record.model_dump_json()
    if tax_folder.contributor and tax_folder.contributor.rut:
        rut_clean = tax_folder.contributor.rut.replace(".", "").replace("-", "").strip()
        if rut_clean and rut_clean in record_json:
            raise ValueError("PII Leak detected: RUT found in telemetry record!")
        if tax_folder.contributor.razon_social and len(tax_folder.contributor.razon_social) > 3:
            if tax_folder.contributor.razon_social.lower() in record_json.lower():
                raise ValueError("PII Leak detected: Razon social found in telemetry record!")

    return record


def enviar_webhook_telemetria(record: AnonymousBenchmarkRecord) -> bool:
    """Envía el registro anónimo vía POST si TELEMETRY_WEBHOOK_URL está configurado."""
    webhook_url = os.environ.get("TELEMETRY_WEBHOOK_URL")
    if not webhook_url:
        return False

    try:
        data = record.model_dump_json().encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Antigravity-Telemetry/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status < 300
    except Exception:
        # Fallo silencioso: la telemetría jamás debe bloquear el procesamiento
        return False


def registrar_telemetria_anonima(tax_folder: TaxFolder) -> AnonymousBenchmarkRecord | None:
    """Procesa y almacena de forma atómica y anónima los ratios de la carpeta tributaria."""
    record = extraer_registro_anonimo(tax_folder)
    if not record:
        return None

    # Registrar en SectorBenchmark local
    try:
        from src.credit.sector_benchmark import SectorBenchmark

        bench = SectorBenchmark()
        bench.registrar_record(record)
    except Exception:
        pass

    # Enviar a webhook opcional si configurado
    enviar_webhook_telemetria(record)

    return record
