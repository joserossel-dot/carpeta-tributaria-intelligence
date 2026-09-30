import io
import re
from decimal import Decimal
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from src.models.tax_folder import TaxFolder
from src.utils.formatting import fmt_date, format_mclp


class ExcelReport:
    """Generador de Cartola y Dictamen de Comité en formato Excel (.xlsx) 100% en RAM."""

    def __init__(self) -> None:
        self.header_fill = PatternFill(
            start_color="0F172A", end_color="0F172A", fill_type="solid"
        )
        self.subheader_fill = PatternFill(
            start_color="1E293B", end_color="1E293B", fill_type="solid"
        )
        self.zebra_fill = PatternFill(
            start_color="F8FAFC", end_color="F8FAFC", fill_type="solid"
        )
        self.accent_fill = PatternFill(
            start_color="EFF6FF", end_color="EFF6FF", fill_type="solid"
        )

        self.font_title = Font(name="Calibri", size=14, bold=True, color="0F172A")
        self.font_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        self.font_bold = Font(name="Calibri", size=10, bold=True, color="0F172A")
        self.font_regular = Font(name="Calibri", size=10, color="1E293B")
        self.font_caption = Font(name="Calibri", size=9, italic=True, color="64748B")

        self.thin_side = Side(border_style="thin", color="CBD5E1")
        self.border_thin = Border(
            left=self.thin_side,
            right=self.thin_side,
            top=self.thin_side,
            bottom=self.thin_side,
        )

    def generate(self, tax_folder: TaxFolder) -> bytes:
        wb = openpyxl.Workbook()
        # Eliminar hoja por defecto
        wb.remove(wb.active)

        self._build_dictamen_sheet(wb, tax_folder)
        self._build_f29_sheet(wb, tax_folder)
        self._build_f22_sheet(wb, tax_folder)
        self._build_identificacion_sheet(wb, tax_folder)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def _apply_headers(self, ws, row_idx: int, headers: list[str]) -> None:
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=h)
            cell.fill = self.header_fill
            cell.font = self.font_header
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = self.border_thin

    def _auto_adjust_columns(self, ws, min_width: int = 12, max_width: int = 50) -> None:
        ws.views.sheetView[0].showGridLines = True
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = str(cell.value or "")
                if val:
                    max_len = max(max_len, len(val))
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, min_width), max_width)

    # ------------------------------------------------------------------
    # Pestaña 1: Recomendación Línea (M$)
    # ------------------------------------------------------------------
    def _build_dictamen_sheet(self, wb: openpyxl.Workbook, tf: TaxFolder) -> None:
        ws = wb.create_sheet(title="Recomendación Línea (M$)")
        cr = getattr(tf, "credit_risk", None)
        c = getattr(tf, "contributor", None)

        # Título
        ws.cell(row=1, column=1, value="CAVILARIA SpA — Informe de Evaluación Tributaria y Recomendación de Línea Comercial").font = self.font_title
        ws.cell(
            row=2,
            column=1,
            value="Recomendación Cuantitativa de Línea de Crédito Comercial y Memoria de Cálculo (v2.9.0)",
        ).font = self.font_caption
        ws.cell(
            row=3,
            column=1,
            value="Nota Legal: Cifras en Miles de Pesos Chilenos (M$). Recomendación referencial y no vinculante basada en declaraciones tributarias SII.",
        ).font = self.font_caption

        # Resumen de Evaluación Referencial
        row = 5
        self._apply_headers(ws, row, ["Parámetro de Evaluación", "Recomendación Referencial", "Detalle / Modalidad Sugerida"])
        row += 1

        evaluacion = str(
            getattr(cr, "evaluacion_referencial", None)
            or getattr(cr, "veredicto", "OBSERVADO")
        ).replace("_", " ") if cr else "OBSERVADO"
        score_val = getattr(cr, "score_crediticio", 0.0) if cr else 0.0
        clasif_riesgo = getattr(cr, "clasificacion_riesgo", None) or getattr(cr, "categoria_riesgo", "MODERADO")
        desempeno_texto = getattr(cr, "desempeno_tributario_texto", None) or (
            "Capacidad Operativa Tributaria Alta" if score_val >= 85
            else ("Desempeño Tributario Moderado" if score_val >= 65
                  else "Capacidad Operativa Tributaria Baja (Bloqueo por Pérdida F22)" if (getattr(cr, "bloqueo_por_perdida_tributaria", False))
                  else "Capacidad Operativa Tributaria Baja")
        )
        linea_ini = getattr(cr, "linea_inicial_sugerida", 0) if cr else 0
        linea_max = getattr(cr, "linea_maxima_condicionada", 0) or getattr(cr, "cupo_maximo_sugerido", 0) if cr else 0
        plazo_dias = getattr(cr, "plazo_sugerido_dias", 0) if cr else 0
        plazo_ini = getattr(cr, "plazo_inicial_sugerido", None) or (f"{plazo_dias} días" if plazo_dias > 0 else "Contado")
        resguardo = getattr(cr, "resguardo_comercial_sugerido", None) or getattr(cr, "garantia_exigida", "Venta al contado") if cr else "Venta al contado"
        cond_escalamiento = getattr(cr, "condicion_escalamiento", None) or (
            "Habilitable tras 2 a 3 ciclos de pago completos y oportunos, sujeta a Dicom/Equifax sin morosidad "
            "vigente, constitución de resguardo (pagaré a la vista / seguro de crédito) y validación de estados financieros."
        )
        protocolo = getattr(cr, "protocolo_operativo", None) or "Procedimiento comercial estándar"

        vars_com = getattr(cr, "variables_comerciales", {}) or {}
        boletin_com = vars_com.get("boletin_comercial", "Pendiente de consulta (Condiciona línea)")
        hist_pago = vars_com.get("historial_pago", "Cliente nuevo (Sin historial previo)")

        params = [
            ("Clasificación y Recomendación", evaluacion, f"Categoría de Riesgo: {clasif_riesgo}"),
            ("Puntaje Tributario SII", f"{score_val:.0f} / 100 pts", f"{desempeno_texto} (No reemplaza informe comercial)"),
            ("Línea Inicial Recomendada (M$)", round(linea_ini / 1000.0) if linea_ini else 0, f"Etapa 1 — Apertura controlada ({format_mclp(linea_ini)})"),
            ("Línea Máxima Condicionada (M$)", round(linea_max / 1000.0) if linea_max else 0, f"Etapa 2 — Techo técnico escalonado ({format_mclp(linea_max)})"),
            ("Plazo Inicial Sugerido", plazo_ini, "Plazo de apertura para cliente nuevo o con alertas"),
            ("Plazo Máximo Sugerido", f"{plazo_dias} días" if plazo_dias else "Contado", "Estándar 30 días para crédito comercial tras validación"),
            ("Modalidad y Resguardo Sugerido", resguardo, "Condición legal recomendada para mitigación de riesgo"),
            ("Condición de Escalamiento", cond_escalamiento, "Requisitos para habilitar paso de Línea Inicial a Línea Máxima"),
            ("Boletín Comercial (Dicom/Equifax)", boletin_com, "Variable comercial externa ingresada"),
            ("Historial con Proveedor", hist_pago, "Variable comercial externa ingresada"),
            ("Protocolo Operativo Sugerido", protocolo, "Procedimiento recomendado para despacho y facturación"),
        ]

        for p, r, d in params:
            ws.cell(row=row, column=1, value=p).font = self.font_bold
            c2 = ws.cell(row=row, column=2, value=r)
            c2.font = self.font_bold
            if isinstance(r, (int, float)):
                c2.number_format = "#,##0"
                c2.alignment = Alignment(horizontal="right")
            else:
                c2.alignment = Alignment(horizontal="center")
            ws.cell(row=row, column=3, value=d).font = self.font_regular
            for col in range(1, 4):
                ws.cell(row=row, column=col).border = self.border_thin
            row += 1

        # Filtro de Elegibilidad Tributaria (Etapa 1)
        filtro = getattr(cr, "filtro_elegibilidad", []) or []
        if filtro:
            row += 2
            ws.cell(row=row, column=1, value="Etapa 1: Filtro de Elegibilidad Tributaria").font = self.font_title
            row += 1
            self._apply_headers(ws, row, ["Parámetro de Elegibilidad", "Estado", "Detalle y Verificación Factual"])
            row += 1
            for item in filtro:
                ws.cell(row=row, column=1, value=item.get("parametro", "")).font = self.font_bold
                st_c = ws.cell(row=row, column=2, value=item.get("estado", "OBSERVADO"))
                st_c.font = self.font_bold
                st_c.alignment = Alignment(horizontal="center")
                ws.cell(row=row, column=3, value=item.get("detalle", "")).font = self.font_regular
                for col in range(1, 4):
                    ws.cell(row=row, column=col).border = self.border_thin
                row += 1

        # Desglose del Puntaje Tributario SII (6 Pilares)
        desglose = getattr(cr, "desglose_score", []) or []
        if desglose:
            row += 2
            ws.cell(row=row, column=1, value="Desglose del Puntaje Tributario SII (6 Dimensiones — 100 Puntos)").font = self.font_title
            row += 1
            self._apply_headers(ws, row, ["Pilar Cuantitativo", "Puntaje", "Detalle y Fundamento"])
            row += 1
            for p in desglose:
                ws.cell(row=row, column=1, value=p.nombre).font = self.font_bold
                p_cell = ws.cell(row=row, column=2, value=f"{p.puntaje_obtenido} / {p.puntaje_maximo} pts")
                p_cell.font = self.font_bold
                p_cell.alignment = Alignment(horizontal="center")
                ws.cell(row=row, column=3, value=p.detalle).font = self.font_regular
                for col in range(1, 4):
                    ws.cell(row=row, column=col).border = self.border_thin
                row += 1

        # Memoria de Cálculo (10 Filas de Trazabilidad)
        row += 2
        ws.cell(row=row, column=1, value="Memoria de Cálculo Cuantitativa de Línea Comercial (M$)").font = self.font_title
        row += 1
        self._apply_headers(ws, row, ["Paso del Algoritmo", "Monto (M$)", "Metodología / Fundamento Cuantitativo"])
        row += 1

        mem = getattr(cr, "memoria_calculo", {}) if cr and isinstance(cr.memoria_calculo, dict) else {}
        p_ini = mem.get("periodo_inicio", "")
        p_fin = mem.get("periodo_fin", "")
        v_prom = mem.get("ventas_netas_mensuales_prom", 0)
        base_c = mem.get("base_compras_c_base", 0)
        spread_f29 = mem.get("spread_operacional_f29") or mem.get("brecha_operacional_proxy", 0)
        techo_op = mem.get("techo_operativo_8pct") or mem.get("techo_operativo", 0)
        freno_flujo = mem.get("freno_absorcion_operacional") or mem.get("freno_flujo_operacional_25pct", 0)
        rli_mens = mem.get("rli_mensualizada_f22")
        phi_pct = mem.get("factor_ajuste_conductual_pct", int(round(mem.get("factor_riesgo_phi", 1.0) * 100)))
        cpt_val = mem.get("capital_propio_tributario")
        tope_cpt = mem.get("tope_patrimonial_3pct_cpt") or mem.get("tope_patrimonial_12pct_cpt") or mem.get("tope_patrimonial_cpt")
        cupo_max = mem.get("linea_maxima_condicionada") or mem.get("cupo_maximo_sugerido", 0)
        cupo_ini = mem.get("linea_inicial_sugerida") or linea_ini
        pct_ap = mem.get("pct_apertura_inicial", 50)

        rango_str = f" ({p_ini} a {p_fin})" if p_ini and p_fin else ""
        cpt_str = f"M$ {int(cpt_val // 1000):,}".replace(",", ".") if cpt_val is not None else "Sin F22"

        spread_15 = int(round(spread_f29 * 0.15))
        rli_fallback = mem.get("rli_fallback_8pct", False)
        rli_declarada_le_zero = mem.get("rli_declarada_le_zero", False)
        if rli_declarada_le_zero:
            rli_m_val = format_mclp(mem.get("rli_ultimo_f22"))
            metodologia_b2 = mem.get("glosa_b2") or f"N/A — Línea bloqueada por Pérdida Tributaria en último F22 (Cód. 1695: {rli_m_val})"
        elif not rli_fallback and rli_mens and rli_mens > 0:
            rli_25 = int(round(rli_mens * 0.25))
            metodologia_b2 = f"min(15% Spread F29 [{format_mclp(spread_15)}], 25% RLI Mensual F22 [{format_mclp(rli_25)}]) (Proxy tributario sobre RLI/12; no equivale a flujo de caja libre)"
        else:
            spread_8 = int(round(spread_f29 * 0.08))
            metodologia_b2 = f"8% Spread F29 [{format_mclp(spread_8)}] (penalizado por RLI <= 0 o sin F22) (Proxy tributario sobre RLI/12; no equivale a flujo de caja libre)"

        min_b1_b2 = min(techo_op, freno_flujo)
        if cpt_val is not None and cpt_val <= 0:
            cpt_code_d = mem.get("cpt_source_code") or "645"
            cpt_tipo_d = "CPTS" if cpt_code_d in ("1545", "1546", "1584", "1585") else "CPT"
            glosa_d = mem.get("glosa_paso_d") or f"Bloqueo por {cpt_tipo_d} Negativo en F22 (Cód. {cpt_code_d}: {format_mclp(cpt_val)} -> Tope Patrimonial M$ 0)"
            monto_d_excel = 0
        elif tope_cpt is not None:
            glosa_d = mem.get("glosa_paso_d") or "Tope de concentración por proveedor: 3% CPT; actúa como freno en empresas subcapitalizadas o con CPT <= 0"
            monto_d_excel = round(tope_cpt / 1000.0)
        else:
            glosa_d = "Sin F22 vigente"
            monto_d_excel = "Sin tope"

        phi_val_excel = f"{mem.get('factor_ajuste_conductual_pct', phi_pct)}%"
        glosa_c_excel = mem.get("glosa_paso_c") or "Ajuste por mora F29, postergación IVA y estabilidad YoY"

        calc_steps = [
            (f"Ventas Netas Mensuales Promedio{rango_str}", round(v_prom / 1000.0) if v_prom else 0, "Promedio mensual de ventas de los 12 meses analizados"),
            ("(-) Paso A: Compras Op. Mensuales Promedio (C_base)", round(base_c / 1000.0) if base_c else 0, mem.get("glosa_paso_a") or "Base mensual de compras operacionales 12M (o costo operativo proxy)"),
            ("(=) Spread Operacional Tributario F29", round(spread_f29 / 1000.0) if spread_f29 else 0, "Ventas Netas Mensuales Promedio - Compras Op. Mensuales Promedio"),
            ("Paso B1: Techo por Volumen de Compras (8% C_base)", round(techo_op / 1000.0) if techo_op else 0, "8% sobre C_base (parámetro prudencial de exposición por proveedor: 8% C_base)"),
            ("Paso B2: Freno por Absorción Operacional", round(freno_flujo / 1000.0) if freno_flujo else 0, metodologia_b2),
            ("Paso C: Factor de Ajuste Conductual", phi_val_excel, glosa_c_excel),
            (f"Paso D: Referencia Patrimonial (3% CPT = {cpt_str})", monto_d_excel, glosa_d),
            ("(=) Línea Máxima Condicionada (Techo Técnico)", round(cupo_max / 1000.0) if cupo_max else 0, "min(Techo 8%, Freno Absorción) x Factor Conductual con Tope CPT (truncado a múltiplos de M$ 100)"),
            (
                f"(=) Línea Inicial Recomendada (Etapa 1 - {pct_ap}% Apertura)",
                round(cupo_ini / 1000.0) if cupo_ini else 0,
                mem.get("glosa_apertura")
                or f"{pct_ap}% de Apertura para Score {'>=85' if score_val >= 85 else ('75-84' if score_val >= 75 else ('65-74' if score_val >= 65 else '<65'))} (Tramos: >=85: 50% | 75-84: 40% | 65-74: 30% | <65: 0%)",
            ),
        ]

        for s, v, f in calc_steps:
            ws.cell(row=row, column=1, value=s).font = self.font_bold
            val_cell = ws.cell(row=row, column=2, value=v)
            val_cell.font = self.font_bold
            if isinstance(v, (int, float)):
                val_cell.number_format = "#,##0" if isinstance(v, int) else "0.00"
                val_cell.alignment = Alignment(horizontal="right")
            else:
                val_cell.alignment = Alignment(horizontal="center")
            ws.cell(row=row, column=3, value=f).font = self.font_regular
            for col in range(1, 4):
                ws.cell(row=row, column=col).border = self.border_thin
            row += 1

        # Alertas y Hoja de Ruta
        row += 2
        ws.cell(row=row, column=1, value="Condiciones Suspensivas, Alertas y Monitoreo Sugerido").font = self.font_title
        row += 1
        self._apply_headers(ws, row, ["Tipo", "Descripción", "Observación / Protocolo"])
        row += 1

        banderas = getattr(cr, "banderas_rojas", []) if cr else []
        for b in banderas:
            ws.cell(row=row, column=1, value="Condición Suspensiva / Alerta").font = self.font_bold
            ws.cell(row=row, column=2, value=b).font = self.font_regular
            ws.cell(row=row, column=3, value="Exige validación documental previa (ej. Balance de 8 Columnas)").font = self.font_caption
            for col in range(1, 4):
                ws.cell(row=row, column=col).border = self.border_thin
            row += 1

        hoja_ruta = getattr(cr, "hoja_ruta_comercial", []) if cr else []
        for r in hoja_ruta:
            ws.cell(row=row, column=1, value="Sugerencia / Protocolo").font = self.font_bold
            ws.cell(row=row, column=2, value=r).font = self.font_regular
            ws.cell(row=row, column=3, value="Recomendación operativa y comercial").font = self.font_caption
            for col in range(1, 4):
                ws.cell(row=row, column=col).border = self.border_thin
            row += 1

        self._auto_adjust_columns(ws)

    # ------------------------------------------------------------------
    # Pestaña 2: Flujos F29 (M$)
    # ------------------------------------------------------------------
    def _build_f29_sheet(self, wb: openpyxl.Workbook, tf: TaxFolder) -> None:
        ws = wb.create_sheet(title="Flujos F29 (M$)")
        ws.cell(row=1, column=1, value="Serie Histórica Completa de Declaraciones Mensuales F29 (M$)").font = self.font_title
        ws.cell(row=2, column=1, value="Cifras en Miles de Pesos Chilenos (M$) — Orden: Más reciente a más antiguo").font = self.font_caption

        headers = [
            "Período",
            "Ventas Afectas (M$)",
            "Ventas Exentas (M$)",
            "Exportaciones (M$)",
            "Total Ventas (M$)",
            "Compras Operacionales (M$)",
            "Total Compras (M$)",
            "Débito Fiscal (M$)",
            "Crédito Fiscal (M$)",
            "IVA Determinado (M$)",
            "Postergación IVA",
            "Mora F29 (Cód 94)",
        ]
        self._apply_headers(ws, 4, headers)

        monthly_taxes = getattr(tf, "monthly_taxes", []) or []
        f29_map = {f.periodo: f for f in getattr(tf, "f29", []) or [] if getattr(f, "periodo", None)}

        # Ordenar todos los meses disponibles desde el más reciente al más antiguo
        sorted_mt = sorted(monthly_taxes, key=lambda m: m.periodo or "", reverse=True)

        row = 5
        for mt in sorted_mt:
            p = getattr(mt, "periodo", "")
            f29_obj = f29_map.get(p)
            posterg = "NO"
            mora = "NO"
            if f29_obj:
                cods = {}
                for d in f29_obj.detalles:
                    v_raw = d.valor.replace(".", "").replace("-", "") if d.valor else ""
                    if v_raw.isdigit():
                        cods[d.codigo] = int(v_raw)
                if any(cods.get(c, 0) > 0 for c in ("779", "778", "755", "756")):
                    posterg = "SÍ"
                c92 = cods.get("92", 0)
                c93 = cods.get("93", 0)
                c94 = cods.get("94", 0)
                c91 = cods.get("91", 0)
                recargo = 0
                if c92 > 0 or c93 > 0:
                    recargo = c92 + c93
                elif c91 > 0 and c94 > 0 and c94 > c91:
                    recargo = c94 - c91
                elif c94 > 0 and c91 == 0:
                    recargo = c94
                if recargo > 0:
                    mora = f"SÍ (${recargo:,})".replace(",", ".")

            def to_m(val):
                if val is None:
                    return 0
                return round(float(val) / 1000.0)

            compras_op = getattr(mt, "compras_operacionales", None)
            activo_fijo = getattr(mt, "activo_fijo", None)
            if compras_op is not None:
                total_compras = compras_op + (activo_fijo or Decimal("0"))
            else:
                total_compras = getattr(mt, "compras", None)

            vals = [
                p,
                to_m(getattr(mt, "ventas_afectas", None)),
                to_m(getattr(mt, "ventas_exentas", None)),
                to_m(getattr(mt, "ventas_exportacion", None)),
                to_m(getattr(mt, "total_ventas", None)),
                to_m(compras_op),
                to_m(total_compras),
                to_m(getattr(mt, "debito_fiscal", None)),
                to_m(getattr(mt, "credito_fiscal", None)),
                to_m(getattr(mt, "iva_determinado", None)),
                posterg,
                mora,
            ]

            for col_idx, v in enumerate(vals, 1):
                cell = ws.cell(row=row, column=col_idx, value=v)
                cell.font = self.font_regular
                cell.border = self.border_thin
                if isinstance(v, (int, float)):
                    cell.number_format = "#,##0"
                    cell.alignment = Alignment(horizontal="right")
                else:
                    cell.alignment = Alignment(horizontal="center")

            if row % 2 == 0:
                for col_idx in range(1, len(vals) + 1):
                    ws.cell(row=row, column=col_idx).fill = self.zebra_fill

            row += 1

        self._auto_adjust_columns(ws)

    # ------------------------------------------------------------------
    # Pestaña 3: Patrimonio F22 (M$)
    # ------------------------------------------------------------------
    def _build_f22_sheet(self, wb: openpyxl.Workbook, tf: TaxFolder) -> None:
        ws = wb.create_sheet(title="Patrimonio F22 (M$)")
        ws.cell(row=1, column=1, value="Declaraciones Anuales de Impuesto a la Renta (F22)").font = self.font_title
        ws.cell(row=2, column=1, value="Cifras en Miles de Pesos Chilenos (M$) — Fuente: F22 SII").font = self.font_caption

        headers = [
            "Año Tributario",
            "Ingresos del Giro (M$)",
            "Renta Líquida Imponible (M$)",
            "Capital Propio Tributario (M$)",
            "Impuesto Determinado (M$)",
            "PPM Pagados (M$)",
            "Créditos Imputables (M$)",
            "Pérdidas Tributarias (M$)",
            "Resultado Tributario (M$)",
        ]
        self._apply_headers(ws, 4, headers)

        f22_list = getattr(tf, "f22", []) or []
        sorted_f22 = sorted(f22_list, key=lambda f: f.anio_tributario or "", reverse=True)
        row = 5
        for f in sorted_f22:
            def to_m(val):
                if val is None:
                    return 0
                return round(float(val) / 1000.0)

            vals = [
                str(getattr(f, "anio_tributario", "")),
                to_m(getattr(f, "ingresos", None)),
                to_m(getattr(f, "renta_liquida_imponible", None)),
                to_m(getattr(f, "capital_propio_tributario", None)),
                to_m(getattr(f, "impuesto_determinado", None)),
                to_m(getattr(f, "ppm", None)),
                to_m(getattr(f, "creditos", None)),
                to_m(getattr(f, "perdidas", None)),
                to_m(getattr(f, "resultado_tributario", None)),
            ]

            for col_idx, v in enumerate(vals, 1):
                cell = ws.cell(row=row, column=col_idx, value=v)
                cell.font = self.font_regular
                cell.border = self.border_thin
                if isinstance(v, (int, float)):
                    cell.number_format = "#,##0"
                    cell.alignment = Alignment(horizontal="right")
                else:
                    cell.alignment = Alignment(horizontal="center")

            row += 1

        self._auto_adjust_columns(ws)

    # ------------------------------------------------------------------
    # Pestaña 4: Identificación y Socios
    # ------------------------------------------------------------------
    def _build_identificacion_sheet(self, wb: openpyxl.Workbook, tf: TaxFolder) -> None:
        ws = wb.create_sheet(title="Identificación y Socios")
        c = getattr(tf, "contributor", None)
        kpis = getattr(tf, "kpis", None)

        ws.cell(row=1, column=1, value="Ficha de Contribuyente, Giros y Socios / Representantes").font = self.font_title
        ws.cell(row=2, column=1, value="Extracción automatizada de carpeta tributaria electrónica").font = self.font_caption

        # Datos Generales
        self._apply_headers(ws, 4, ["Campo", "Valor"])
        domicilio_val = getattr(c, "domicilio", None)
        if domicilio_val:
            domicilio_val = re.sub(r"(\d)([a-zA-ZáéíóúñÁÉÍÓÚÑ])", r"\1 \2", domicilio_val)
        else:
            domicilio_val = "No informado"

        datos = [
            ("RUT Contribuyente", getattr(c, "rut", None) or "No informado"),
            ("Razón Social", getattr(c, "razon_social", None) or "No informada"),
            ("Domicilio Legal", domicilio_val),
            ("Comuna", getattr(c, "comuna", None) or "No informada"),
            ("Región", getattr(c, "region", None) or "No informada"),
            ("Fecha Inicio Actividades", fmt_date(getattr(c, "fecha_inicio_actividades", None))),
            ("Régimen Tributario", getattr(c, "regimen_tributario", None) or "No informado"),
            ("Tipo Contribuyente", getattr(c, "tipo_contribuyente", None) or "No informado"),
            ("Fecha Generación Carpeta", fmt_date(getattr(c, "fecha_generacion", None))),
            ("Actividad Principal", getattr(kpis, "principal_activity", None) or "No informada"),
        ]

        row = 5
        for k, v in datos:
            ws.cell(row=row, column=1, value=k).font = self.font_bold
            ws.cell(row=row, column=2, value=v).font = self.font_regular
            ws.cell(row=row, column=1).border = self.border_thin
            ws.cell(row=row, column=2).border = self.border_thin
            row += 1

        # Giros SII
        row += 2
        ws.cell(row=row, column=1, value="Actividades Económicas (Giros SII)").font = self.font_title
        row += 1
        self._apply_headers(ws, row, ["Código", "Descripción del Giro", "Principal", "Categoría"])
        row += 1

        activities = getattr(tf, "activities", []) or []
        for act in activities:
            ws.cell(row=row, column=1, value=getattr(act, "codigo", "")).font = self.font_regular
            ws.cell(row=row, column=2, value=getattr(act, "descripcion", "")).font = self.font_regular
            ws.cell(row=row, column=3, value="SÍ" if getattr(act, "principal", False) else "NO").font = self.font_regular
            ws.cell(row=row, column=4, value=getattr(act, "categoria", "") or "").font = self.font_regular
            for col in range(1, 5):
                ws.cell(row=row, column=col).border = self.border_thin
            row += 1

        # Representantes Legales / Socios
        row += 2
        ws.cell(row=row, column=1, value="Representantes Legales y Socios Registrados").font = self.font_title
        row += 1
        self._apply_headers(ws, row, ["RUT", "Nombre Completo", "Cargo / Relación"])
        row += 1

        reps = getattr(tf, "representatives", []) or []
        for r in reps:
            ws.cell(row=row, column=1, value=getattr(r, "rut", "")).font = self.font_regular
            ws.cell(row=row, column=2, value=getattr(r, "nombre", "")).font = self.font_regular
            ws.cell(row=row, column=3, value=getattr(r, "cargo", "") or "Representante Legal").font = self.font_regular
            for col in range(1, 4):
                ws.cell(row=row, column=col).border = self.border_thin
            row += 1

        self._auto_adjust_columns(ws)
