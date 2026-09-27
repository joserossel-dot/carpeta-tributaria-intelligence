import io
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
        ws.cell(row=1, column=1, value="CAVILARIA SpA — Evaluación Tributaria y Recomendación de Crédito Comercial").font = self.font_title
        ws.cell(
            row=2,
            column=1,
            value="Recomendación Cuantitativa de Línea de Crédito Comercial y Memoria de Cálculo (v2.2)",
        ).font = self.font_caption
        ws.cell(
            row=3,
            column=1,
            value="Nota Legal: Cifras en Miles de Pesos Chilenos (M$). Recomendación referencial y no vinculante basada en declaraciones tributarias SII.",
        ).font = self.font_caption

        # Resumen de Evaluación Referencial
        row = 5
        self._apply_headers(ws, row, ["Parámetro de Evaluación", "Recomendación Referencial", "Detalle / Resguardo"])
        row += 1

        evaluacion = str(
            getattr(cr, "evaluacion_referencial", None)
            or getattr(cr, "veredicto", "OBSERVADO")
        ).replace("_", " ") if cr else "OBSERVADO"
        score_val = getattr(cr, "score_crediticio", 0.0) if cr else 0.0
        cat_val = getattr(cr, "categoria_riesgo", "MEDIO") if cr else "MEDIO"
        cupo_ap = getattr(cr, "cupo_aprobado", 0) if cr else 0
        plazo_dias = getattr(cr, "plazo_sugerido_dias", 0) if cr else 0
        resguardo = getattr(cr, "resguardo_comercial_sugerido", None) or getattr(cr, "garantia_exigida", "Venta al contado") if cr else "Venta al contado"
        protocolo = getattr(cr, "protocolo_operativo", None) or "Procedimiento comercial estándar"

        params = [
            ("Evaluación Referencial", evaluacion, f"Categoría de Riesgo: {cat_val}"),
            ("Score Crediticio", f"{score_val:.1f} / 100", f"Evaluación cuantitativa sobre declaraciones tributarias SII"),
            ("Línea Máxima Sugerida (M$)", round(cupo_ap / 1000.0) if cupo_ap else 0, f"Equivalente a {format_mclp(cupo_ap)}"),
            ("Plazo Sugerido", f"{plazo_dias} días" if plazo_dias else "Contado", "Estándar máximo 30 días para crédito comercial" if plazo_dias else "Pago anticipado o contra entrega"),
            ("Resguardo Comercial Sugerido", resguardo, "Condición legal recomendada para mitigación de riesgo"),
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

        # Memoria de Cálculo
        row += 2
        ws.cell(row=row, column=1, value="Memoria de Cálculo Cuantitativa de Línea Comercial (M$)").font = self.font_title
        row += 1
        self._apply_headers(ws, row, ["Paso del Algoritmo", "Monto (M$)", "Metodología / Fundamento Cuantitativo"])
        row += 1

        mem = getattr(cr, "memoria_calculo", {}) if cr and isinstance(cr.memoria_calculo, dict) else {}
        base_c = mem.get("base_compras_c_base") or mem.get("base_compras_mensual_operacional", 0)
        techo_op = mem.get("techo_operativo_8pct") or mem.get("techo_operativo", 0)
        freno_flujo = mem.get("freno_flujo_operacional_25pct", 0)
        phi_v = mem.get("factor_riesgo_phi") or mem.get("factor_phi_calidad_crediticia", 1.0)
        cupo_pre = mem.get("cupo_preliminar", 0)
        cpt_val = mem.get("capital_propio_tributario")
        tope_cpt = mem.get("tope_patrimonial_cpt") or mem.get("tope_patrimonial_12pct_cpt") or mem.get("tope_patrimonial_35pct_cpt")
        cupo_max = mem.get("cupo_maximo_sugerido", 0)

        calc_steps = [
            ("Paso A: Base de Compras Operacionales (C_base)", round(base_c / 1000.0) if base_c else 0, "Promedio mensual compras netas 12M o costo operativo proxy"),
            ("Paso B: Techo Operativo Proveedor (8%)", round(techo_op / 1000.0) if techo_op else 0, "Techo de absorción individual conservador por proveedor (8%)"),
            ("Freno de Flujo Operacional Neto (25%)", round(freno_flujo / 1000.0) if freno_flujo else 0, "25% del Margen Operacional Mensual Depurado [Ventas - Compras - IVA Det.]"),
            ("Paso C: Factor de Ajuste Conductual", round(phi_v, 2), "Factor de ajuste conductual por mora F29, postergación y variaciones de venta"),
            ("Cupo Preliminar Ajustado por Riesgo", round(cupo_pre / 1000.0) if cupo_pre else 0, "min(Techo 8%, Freno Flujo 25%) × Factor Conductual"),
            ("Capital Propio Tributario (CPT)", round(cpt_val / 1000.0) if cpt_val is not None else "Sin F22", "Patrimonio tributario según declaración anual de renta (F22)"),
            ("Paso D: Freno Patrimonial CPT", round(tope_cpt / 1000.0) if tope_cpt is not None else "Sin tope", "12% CPT en línea limpia / 20% con garantías ($0 si CPT <= 0)"),
            ("Línea Máxima Sugerida Final", round(cupo_max / 1000.0) if cupo_max else 0, "Redondeo limpio a múltiplos de M$ 100 ($100.000 CLP)"),
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
        ws.cell(row=row, column=1, value="Alertas y Recomendaciones Comerciales").font = self.font_title
        row += 1
        self._apply_headers(ws, row, ["Tipo", "Descripción", "Observación / Sugerencia"])
        row += 1

        banderas = getattr(cr, "banderas_rojas", []) if cr else []
        for b in banderas:
            ws.cell(row=row, column=1, value="Alerta Forense").font = self.font_bold
            ws.cell(row=row, column=2, value=b).font = self.font_regular
            ws.cell(row=row, column=3, value="Riesgo de insolvencia o mora tributaria").font = self.font_caption
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
                for d in f29_obj.detalles:
                    if d.codigo in ("779", "755", "756") and d.valor and d.valor.replace(".", "").isdigit() and int(d.valor.replace(".", "")) > 0:
                        posterg = "SÍ"
                    if d.codigo == "94" and d.valor and d.valor.replace(".", "").isdigit() and int(d.valor.replace(".", "")) > 0:
                        mora = f"SÍ (${int(d.valor.replace('.', '')):,})".replace(",", ".")

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
        datos = [
            ("RUT Contribuyente", getattr(c, "rut", None) or "No informado"),
            ("Razón Social", getattr(c, "razon_social", None) or "No informada"),
            ("Domicilio Legal", getattr(c, "domicilio", None) or "No informado"),
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
