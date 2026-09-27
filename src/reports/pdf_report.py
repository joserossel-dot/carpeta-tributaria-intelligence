import io
from decimal import Decimal
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.models.tax_folder import TaxFolder
from src.utils.formatting import fmt_date, format_mclp


class PDFReport:
    """Generador de Dictamen Ejecutivo en formato PDF corporativo (100% en RAM)."""

    def generate(self, tax_folder: TaxFolder) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=14 * mm,
            rightMargin=14 * mm,
            topMargin=12 * mm,
            bottomMargin=12 * mm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#0F172A"),
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#475569"),
        )
        h2_style = ParagraphStyle(
            "SectionH2",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=6,
            spaceAfter=4,
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor("#1E293B"),
        )
        body_bold = ParagraphStyle(
            "DocBodyBold",
            parent=body_style,
            fontName="Helvetica-Bold",
        )
        table_cell = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#1E293B"),
        )
        table_cell_bold = ParagraphStyle(
            "TableCellBold",
            parent=table_cell,
            fontName="Helvetica-Bold",
        )
        table_cell_header = ParagraphStyle(
            "TableCellHeader",
            parent=table_cell,
            fontName="Helvetica-Bold",
            textColor=colors.white,
        )
        badge_style = ParagraphStyle(
            "BadgeStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=1,
            textColor=colors.white,
        )

        story: list[Any] = []

        # 1. ENCABEZADO CORPORATIVO
        story.append(Paragraph("CAVILARIA SpA — Comité de Crédito B2B", title_style))
        story.append(
            Paragraph(
                "Dictamen Ejecutivo de Evaluación Cuantitativa y Asignación de Cupo Comercial (v2.2)",
                subtitle_style,
            )
        )
        story.append(Spacer(1, 2 * mm))

        # Sello de Retención Cero
        sello_html = (
            "<b>🔒 SELLO DE RETENCIÓN CERO (Zero-PII):</b> Procesado 100% en memoria volátil RAM. "
            "Sin persistencia de archivos, Razón Social ni RUTs en disco conforme a la Ley N° 21.719."
        )
        sello_data = [[Paragraph(sello_html, body_style)]]
        sello_table = Table(sello_data, colWidths=[185 * mm])
        sello_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(sello_table)
        story.append(Spacer(1, 3 * mm))

        # 2. IDENTIFICACIÓN DEL CONTRIBUYENTE
        c = getattr(tax_folder, "contributor", None)
        kpis = getattr(tax_folder, "kpis", None)
        rut = getattr(c, "rut", None) or "No informado"
        razon_social = getattr(c, "razon_social", None) or "No informada"
        domicilio = getattr(c, "domicilio", None) or "No informado"
        comuna_region = f"{getattr(c, 'comuna', None) or '—'}, {getattr(c, 'region', None) or '—'}"
        ini_act = fmt_date(getattr(c, "fecha_inicio_actividades", None)) or "No informado"
        regimen = getattr(c, "regimen_tributario", None) or "No informado"
        giro_prin = getattr(kpis, "principal_activity", None) or "No informada"

        contrib_data = [
            [
                Paragraph("<b>RUT:</b> " + rut, body_style),
                Paragraph("<b>Razón Social:</b> " + razon_social, body_style),
            ],
            [
                Paragraph("<b>Domicilio:</b> " + domicilio, body_style),
                Paragraph("<b>Comuna / Región:</b> " + comuna_region, body_style),
            ],
            [
                Paragraph("<b>Inicio Actividades:</b> " + ini_act, body_style),
                Paragraph("<b>Régimen Tributario:</b> " + regimen, body_style),
            ],
            [
                Paragraph("<b>Giro Principal SII:</b> " + giro_prin, body_style),
                Paragraph("<b>Meses F29 Auditados:</b> " + str(getattr(kpis, "f29_count", 0)), body_style),
            ],
        ]
        contrib_table = Table(contrib_data, colWidths=[92.5 * mm, 92.5 * mm])
        contrib_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        story.append(contrib_table)
        story.append(Spacer(1, 3 * mm))

        # 3. VEREDICTO DE COMITÉ Y CUPO APROBADO
        cr = getattr(tax_folder, "credit_risk", None)
        veredicto = str(getattr(cr, "veredicto", "OBSERVADO")) if cr else "OBSERVADO"
        score_val = getattr(cr, "score_crediticio", 0.0) if cr else 0.0
        cat_val = getattr(cr, "categoria_riesgo", "MEDIO") if cr else "MEDIO"
        cupo_ap = getattr(cr, "cupo_aprobado", 0) if cr else 0
        plazo_dias = getattr(cr, "plazo_sugerido_dias", 0) if cr else 0
        garantia = getattr(cr, "garantia_exigida", "Venta contado") if cr else "Venta contado"
        dictamen = getattr(cr, "dictamen_ejecutivo", "En evaluación") if cr else "En evaluación"

        # Color del veredicto
        if "RECHAZADO" in veredicto:
            badge_bg = colors.HexColor("#DC2626")
        elif "APROBADO_CON_CONDICIONES" in veredicto:
            badge_bg = colors.HexColor("#D97706")
        elif "APROBADO" in veredicto:
            badge_bg = colors.HexColor("#16A34A")
        else:
            badge_bg = colors.HexColor("#475569")

        veredicto_txt = veredicto.replace("_", " ")
        veredicto_cell = Paragraph(f"<b>{veredicto_txt}</b>", badge_style)
        cupo_ap_txt = format_mclp(cupo_ap)

        panel_data = [
            [
                Paragraph("<b>VEREDICTO COMITÉ</b>", table_cell_header),
                Paragraph("<b>SCORE CREDITICIO</b>", table_cell_header),
                Paragraph("<b>CUPO APROBADO (M$)</b>", table_cell_header),
                Paragraph("<b>PLAZO Y GARANTÍA</b>", table_cell_header),
            ],
            [
                veredicto_cell,
                Paragraph(f"<b>{score_val:.1f} / 100</b><br/>{cat_val}", table_cell_bold),
                Paragraph(f"<font size=11><b>{cupo_ap_txt}</b></font>", table_cell_bold),
                Paragraph(f"<b>{plazo_dias} días</b><br/>{garantia}", table_cell),
            ],
        ]
        panel_table = Table(panel_data, colWidths=[46 * mm, 42 * mm, 47 * mm, 50 * mm])
        panel_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("BACKGROUND", (0, 1), (0, 1), badge_bg),
                ("BACKGROUND", (1, 1), (-1, 1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0F172A")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        story.append(panel_table)

        # Dictamen
        story.append(Spacer(1, 2 * mm))
        dictamen_html = f"<b>Dictamen del Comité:</b> {dictamen}"
        dictamen_table = Table([[Paragraph(dictamen_html, body_style)]], colWidths=[185 * mm])
        dictamen_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        story.append(dictamen_table)
        story.append(Spacer(1, 3 * mm))

        # 4. MEMORIA DE CÁLCULO CUANTITATIVA (M$)
        mem = getattr(cr, "memoria_calculo", {}) if cr and isinstance(cr.memoria_calculo, dict) else {}
        base_c = mem.get("base_compras_c_base") or mem.get("base_compras_mensual_operacional", 0)
        techo_op = mem.get("techo_operativo_8pct") or mem.get("techo_operativo", 0)
        freno_flujo = mem.get("freno_flujo_operacional_25pct", 0)
        phi_v = mem.get("factor_riesgo_phi") or mem.get("factor_phi_calidad_crediticia", 1.0)
        cupo_pre = mem.get("cupo_preliminar", 0)
        cpt_val = mem.get("capital_propio_tributario")
        tope_cpt = mem.get("tope_patrimonial_cpt") or mem.get("tope_patrimonial_12pct_cpt") or mem.get("tope_patrimonial_35pct_cpt")
        cupo_max = mem.get("cupo_maximo_sugerido", 0)

        mem_rows = [
            [
                Paragraph("<b>Etapa Cuantitativa</b>", table_cell_header),
                Paragraph("<b>Fórmula / Parámetro Estándar</b>", table_cell_header),
                Paragraph("<b>Monto (M$)</b>", table_cell_header),
            ],
            [
                Paragraph("Paso A: Base de Compras (C_base)", table_cell_bold),
                Paragraph("Promedio mensual compras operacionales 12M (o costo proxy)", table_cell),
                Paragraph(format_mclp(base_c), table_cell_bold),
            ],
            [
                Paragraph("Paso B: Techo Operativo Proveedor (8%)", table_cell_bold),
                Paragraph("8% sobre C_base (estándar bancario individual)", table_cell),
                Paragraph(format_mclp(techo_op), table_cell_bold),
            ],
            [
                Paragraph("Freno Flujo Neto Depurado (25%)", table_cell_bold),
                Paragraph("Máx. 25% de [Ventas 12M - Compras Op. 12M - IVA Det. 12M]", table_cell),
                Paragraph(format_mclp(freno_flujo), table_cell_bold),
            ],
            [
                Paragraph("Paso C: Factor de Calidad Crediticia (Φ)", table_cell_bold),
                Paragraph("Castigos objetivos por mora F29, postergación IVA y caída YoY", table_cell),
                Paragraph(f"Φ = {phi_v:.2f}", table_cell_bold),
            ],
            [
                Paragraph("Cupo Preliminar Ajustado por Riesgo", table_cell_bold),
                Paragraph("min(Techo 8%, Freno Flujo 25%) × Φ", table_cell),
                Paragraph(format_mclp(cupo_pre), table_cell_bold),
            ],
            [
                Paragraph("Capital Propio Tributario (CPT)", table_cell_bold),
                Paragraph("Patrimonio fiscal declarado en último F22 disponible", table_cell),
                Paragraph(format_mclp(cpt_val) if cpt_val is not None else "Sin F22", table_cell_bold),
            ],
            [
                Paragraph("Paso D: Freno Patrimonial CPT", table_cell_bold),
                Paragraph("12% CPT en línea limpia / 20% con aval ($0 si CPT <= 0)", table_cell),
                Paragraph(format_mclp(tope_cpt) if tope_cpt is not None else "Sin tope", table_cell_bold),
            ],
            [
                Paragraph("Cupo Máximo Sugerido Final", table_cell_bold),
                Paragraph("Redondeo a múltiplos de $100.000 CLP (M$ 100)", table_cell),
                Paragraph(format_mclp(cupo_max), table_cell_bold),
            ],
        ]
        mem_table = Table(mem_rows, colWidths=[60 * mm, 95 * mm, 30 * mm])
        mem_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#FFFFFF")),
                ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#F8FAFC")),
                ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#FFFFFF")),
                ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#F8FAFC")),
                ("BACKGROUND", (0, 5), (-1, 5), colors.HexColor("#FFFFFF")),
                ("BACKGROUND", (0, 6), (-1, 6), colors.HexColor("#F8FAFC")),
                ("BACKGROUND", (0, 7), (-1, 7), colors.HexColor("#FFFFFF")),
                ("BACKGROUND", (0, 8), (-1, 8), colors.HexColor("#E2E8F0")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 2.2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
                ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ])
        )
        story.append(Paragraph("Memoria de Cálculo Cuantitativa (M$)", h2_style))
        story.append(mem_table)
        story.append(Spacer(1, 2 * mm))

        # 5. BANDERAS ROJAS Y HOJA DE RUTA
        banderas = getattr(cr, "banderas_rojas", []) if cr else []
        hoja_ruta = getattr(cr, "hoja_ruta_comercial", []) if cr else []

        flags_p = []
        if banderas:
            for b in banderas:
                flags_p.append(Paragraph(f"🔴 <b>Bandera Roja:</b> {b}", body_style))
        else:
            flags_p.append(Paragraph("🟢 <i>Sin banderas rojas críticas detectadas en el análisis.</i>", body_style))

        hr_p = []
        if hoja_ruta:
            for r in hoja_ruta:
                hr_p.append(Paragraph(f"🧭 <b>Recomendación:</b> {r}", body_style))
        else:
            hr_p.append(Paragraph("<i>Sin recomendaciones adicionales.</i>", body_style))

        flags_table = Table([[flags_p, hr_p]], colWidths=[92.5 * mm, 92.5 * mm])
        flags_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        story.append(flags_table)
        story.append(Spacer(1, 3 * mm))

        # 6. TABLA RESUMEN F29 (Últimos 12 meses en M$)
        monthly_taxes = getattr(tax_folder, "monthly_taxes", []) or []
        if monthly_taxes:
            f29_header = [
                Paragraph("<b>Período</b>", table_cell_header),
                Paragraph("<b>Ventas (M$)</b>", table_cell_header),
                Paragraph("<b>Compras (M$)</b>", table_cell_header),
                Paragraph("<b>Débito (M$)</b>", table_cell_header),
                Paragraph("<b>Crédito (M$)</b>", table_cell_header),
                Paragraph("<b>IVA Det. (M$)</b>", table_cell_header),
            ]
            f29_rows = [f29_header]
            for mt in monthly_taxes[:12]:
                f29_rows.append([
                    Paragraph(getattr(mt, "periodo", ""), table_cell),
                    Paragraph(format_mclp(getattr(mt, "total_ventas", None)), table_cell),
                    Paragraph(format_mclp(getattr(mt, "compras", None)), table_cell),
                    Paragraph(format_mclp(getattr(mt, "debito_fiscal", None)), table_cell),
                    Paragraph(format_mclp(getattr(mt, "credito_fiscal", None)), table_cell),
                    Paragraph(format_mclp(getattr(mt, "iva_determinado", None)), table_cell),
                ])
            f29_table = Table(f29_rows, colWidths=[25 * mm, 32 * mm, 32 * mm, 32 * mm, 32 * mm, 32 * mm])
            f29_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 1.8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ])
            )
            story.append(KeepTogether([
                Paragraph("Resumen de Declaraciones Mensuales F29 (Últimos 12 Meses en M$)", h2_style),
                f29_table,
            ]))

        # 7. TABLA RESUMEN F22 (Anual en M$)
        f22_list = getattr(tax_folder, "f22", []) or []
        if f22_list:
            story.append(Spacer(1, 2 * mm))
            f22_header = [
                Paragraph("<b>Año</b>", table_cell_header),
                Paragraph("<b>Ingresos (M$)</b>", table_cell_header),
                Paragraph("<b>RLI (M$)</b>", table_cell_header),
                Paragraph("<b>Capital Propio CPT (M$)</b>", table_cell_header),
                Paragraph("<b>Impuesto Det. (M$)</b>", table_cell_header),
            ]
            f22_rows = [f22_header]
            for f in f22_list:
                f22_rows.append([
                    Paragraph(str(getattr(f, "anio_tributario", "")), table_cell),
                    Paragraph(format_mclp(getattr(f, "ingresos", None)), table_cell),
                    Paragraph(format_mclp(getattr(f, "renta_liquida_imponible", None)), table_cell),
                    Paragraph(format_mclp(getattr(f, "capital_propio_tributario", None)), table_cell),
                    Paragraph(format_mclp(getattr(f, "impuesto_determinado", None)), table_cell),
                ])
            f22_table = Table(f22_rows, colWidths=[25 * mm, 40 * mm, 40 * mm, 45 * mm, 35 * mm])
            f22_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 1.8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ])
            )
            story.append(KeepTogether([
                Paragraph("Resumen de Declaraciones Anuales F22 (Patrimonio e Impuesto a la Renta en M$)", h2_style),
                f22_table,
            ]))

        # Footer nota M$
        story.append(Spacer(1, 3 * mm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=3))
        nota_pie = (
            "<i>Nota: Cifras expresadas en Miles de Pesos Chilenos (M$). "
            "Dictamen emitido automáticamente conforme a los criterios objetivos del Comité de Riesgo y Crédito B2B de Cavilaria SpA. "
            "Procesamiento seguro en RAM sin almacenamiento de datos (Zero-PII).</i>"
        )
        story.append(Paragraph(nota_pie, ParagraphStyle("NotaPie", parent=body_style, fontSize=7, leading=9, textColor=colors.HexColor("#64748B"))))

        doc.build(story)
        return buffer.getvalue()
