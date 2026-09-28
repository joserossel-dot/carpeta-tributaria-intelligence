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
            topMargin=10 * mm,
            bottomMargin=10 * mm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            textColor=colors.HexColor("#0F172A"),
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#475569"),
        )
        h2_style = ParagraphStyle(
            "SectionH2",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=4,
            spaceAfter=3,
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
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
            fontSize=7,
            leading=8.5,
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
            fontSize=8.5,
            leading=10.5,
            alignment=1,
            textColor=colors.white,
        )

        story: list[Any] = []

        # 1. ENCABEZADO CORPORATIVO
        story.append(Paragraph("CAVILARIA SpA — Informe de Evaluación Tributaria y Recomendación de Línea Comercial", title_style))
        story.append(
            Paragraph(
                "Informe Cuantitativo Referencial para Otorgamiento de Crédito Comercial B2B (v2.4)",
                subtitle_style,
            )
        )
        story.append(Spacer(1, 2 * mm))

        # 2. IDENTIFICACIÓN DEL CONTRIBUYENTE Y VIGENCIA
        c = getattr(tax_folder, "contributor", None)
        kpis = getattr(tax_folder, "kpis", None)
        cr = getattr(tax_folder, "credit_risk", None)

        rut = getattr(c, "rut", None) or "No informado"
        razon_social = getattr(c, "razon_social", None) or "No informada"
        domicilio = getattr(c, "domicilio", None) or "No informado"
        comuna_region = f"{getattr(c, 'comuna', None) or '—'}, {getattr(c, 'region', None) or '—'}"
        ini_act = fmt_date(getattr(c, "fecha_inicio_actividades", None)) or "No informado"
        regimen = getattr(c, "regimen_tributario", None) or "No informado"
        giro_prin = getattr(kpis, "principal_activity", None) or "No informada"

        vigencia = getattr(cr, "vigencia_datos", {}) or {}
        bienes_raices = getattr(cr, "bienes_raices_resumen", None) or "No registra bienes raíces en carpeta"
        fecha_emision = vigencia.get("fecha_emision", "No informada")
        ult_periodo = vigencia.get("ultimo_periodo", "No informado")
        desfase_m = vigencia.get("meses_desfase", 0)
        confianza_vig = vigencia.get("nivel_confianza", "MEDIA")

        vars_com = getattr(cr, "variables_comerciales", {}) or {}
        boletin_com = vars_com.get("boletin_comercial", "Pendiente de consulta (Condiciona línea)")
        hist_pago = vars_com.get("historial_pago", "Cliente nuevo (Sin historial previo)")

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
                Paragraph(f"<b>Bienes Raíces:</b> {bienes_raices}", body_style),
            ],
            [
                Paragraph(f"<b>Emisión Carpeta:</b> {fecha_emision} | <b>Último F29:</b> {ult_periodo}", body_style),
                Paragraph(f"<b>Antigüedad del Dato:</b> {desfase_m} meses (Confianza: <b>{confianza_vig}</b>)", body_style),
            ],
            [
                Paragraph(f"<b>Boletín Comercial (Dicom):</b> {boletin_com}", body_style),
                Paragraph(f"<b>Historial con Proveedor:</b> {hist_pago}", body_style),
            ],
        ]
        contrib_table = Table(contrib_data, colWidths=[92.5 * mm, 92.5 * mm])
        contrib_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 1.8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        story.append(contrib_table)
        story.append(Spacer(1, 2 * mm))

        # 3. RESUMEN RECOMENDACIÓN REFERENCIAL (PANEL EJECUTIVO)
        evaluacion = str(
            getattr(cr, "evaluacion_referencial", None)
            or getattr(cr, "veredicto", "OBSERVADO")
        ) if cr else "OBSERVADO"
        score_val = getattr(cr, "score_crediticio", 0.0) if cr else 0.0
        clasif_riesgo = getattr(cr, "clasificacion_riesgo", None) or getattr(cr, "categoria_riesgo", "MODERADO")
        desempeno_texto = getattr(cr, "desempeno_tributario_texto", None) or ("Desempeño Tributario Alto" if score_val >= 80 else "Desempeño Tributario Medio")
        linea_ini = getattr(cr, "linea_inicial_sugerida", 0) if cr else 0
        linea_max = getattr(cr, "linea_maxima_condicionada", 0) or getattr(cr, "cupo_maximo_sugerido", 0) if cr else 0
        plazo_dias = getattr(cr, "plazo_sugerido_dias", 0) if cr else 0
        plazo_ini = getattr(cr, "plazo_inicial_sugerido", None) or (f"{plazo_dias} días" if plazo_dias > 0 else "Contado")
        resguardo = getattr(cr, "resguardo_comercial_sugerido", None) or getattr(cr, "garantia_exigida", "Venta al contado") if cr else "Venta al contado"

        # Color de la evaluación referencial
        if "BAJO" in evaluacion:
            badge_bg = colors.HexColor("#16A34A")
        elif "MODERADO" in evaluacion or "MEDIO" in evaluacion or "CONDICIONES" in evaluacion:
            badge_bg = colors.HexColor("#D97706")
        elif "ALTO" in evaluacion or "RECHAZADO" in evaluacion:
            badge_bg = colors.HexColor("#DC2626")
        else:
            badge_bg = colors.HexColor("#475569")

        evaluacion_cell = Paragraph(f"<b>{evaluacion}</b>", badge_style)
        linea_ini_txt = format_mclp(linea_ini)
        linea_max_txt = format_mclp(linea_max)

        panel_data = [
            [
                Paragraph("<b>CLASIFICACIÓN Y RECOMENDACIÓN</b>", table_cell_header),
                Paragraph("<b>PUNTAJE TRIBUTARIO SII</b>", table_cell_header),
                Paragraph("<b>LÍNEA ESCALONADA (M$)</b>", table_cell_header),
                Paragraph("<b>PLAZO Y CONDICIONES DE RESGUARDO</b>", table_cell_header),
            ],
            [
                evaluacion_cell,
                Paragraph(f"<b>{score_val:.0f} / 100 pts</b><br/>{desempeno_texto}<br/><font size=5.5 color='#64748B'>No reemplaza informe comercial</font>", table_cell_bold),
                Paragraph(f"<b>Inicial: {linea_ini_txt}</b><br/><font size=6.5>Máxima: {linea_max_txt}</font>", table_cell_bold),
                Paragraph(f"<b>Plazo Inicial: {plazo_ini}</b><br/><font size=5.5>{resguardo}</font>", table_cell),
            ],
        ]
        panel_table = Table(panel_data, colWidths=[54 * mm, 38 * mm, 38 * mm, 55 * mm])
        panel_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("BACKGROUND", (0, 1), (0, 1), badge_bg),
                ("BACKGROUND", (1, 1), (-1, 1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0F172A")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ])
        )
        story.append(panel_table)
        story.append(Spacer(1, 2 * mm))

        # 3.1 FILTRO DE ELEGIBILIDAD TRIBUTARIA (ETAPA 1)
        filtro = getattr(cr, "filtro_elegibilidad", []) or []
        if filtro:
            filtro_rows = [
                [
                    Paragraph("<b>Filtro de Elegibilidad Tributaria (Etapa 1)</b>", table_cell_header),
                    Paragraph("<b>Estado</b>", table_cell_header),
                    Paragraph("<b>Detalle y Verificación Factual</b>", table_cell_header),
                ]
            ]
            for item in filtro:
                st_txt = item.get("estado", "OBSERVADO")
                st_color = "#16A34A" if st_txt == "CUMPLE" else "#EA580C"
                filtro_rows.append([
                    Paragraph(item.get("parametro", ""), table_cell_bold),
                    Paragraph(f"<font color='{st_color}'><b>{st_txt}</b></font>", table_cell_bold),
                    Paragraph(item.get("detalle", ""), table_cell),
                ])
            filtro_table = Table(filtro_rows, colWidths=[62 * mm, 25 * mm, 98 * mm])
            filtro_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFFFFF")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
                    ("ALIGN", (1, 0), (1, -1), "CENTER"),
                ])
            )
            story.append(filtro_table)
            story.append(Spacer(1, 2 * mm))

        # 4. DESGLOSE DEL PUNTAJE TRIBUTARIO SII (6 PILARES - 100 PTS)
        desglose = getattr(cr, "desglose_score", []) or []
        if desglose:
            score_rows = [
                [
                    Paragraph("<b>Pilar Cuantitativo</b>", table_cell_header),
                    Paragraph("<b>Puntaje</b>", table_cell_header),
                    Paragraph("<b>Máx.</b>", table_cell_header),
                    Paragraph("<b>Fundamento y Detalle del Indicador</b>", table_cell_header),
                ]
            ]
            for p in desglose:
                score_rows.append([
                    Paragraph(getattr(p, "nombre", ""), table_cell_bold),
                    Paragraph(f"{getattr(p, 'puntaje_obtenido', 0)} pts", table_cell_bold),
                    Paragraph(f"{getattr(p, 'puntaje_maximo', 0)} pts", table_cell),
                    Paragraph(getattr(p, "detalle", ""), table_cell),
                ])
            score_rows.append([
                Paragraph("<b>Total Puntaje Tributario SII</b>", table_cell_bold),
                Paragraph(f"<b>{score_val:.0f} pts</b>", table_cell_bold),
                Paragraph("<b>100 pts</b>", table_cell_bold),
                Paragraph(f"<b>Calificación: {desempeno_texto} (Clasificación de Riesgo: {clasif_riesgo})</b>", table_cell_bold),
            ])
            score_table = Table(score_rows, colWidths=[55 * mm, 18 * mm, 16 * mm, 96 * mm])
            score_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                    ("BACKGROUND", (0, 1), (-1, -2), colors.HexColor("#FFFFFF")),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 1.6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
                    ("ALIGN", (1, 0), (2, -1), "CENTER"),
                ])
            )
            story.append(Paragraph("Desglose del Puntaje Tributario SII (6 Dimensiones — 100 Puntos)", h2_style))
            story.append(score_table)
            story.append(Spacer(1, 2 * mm))

        # 5. MEMORIA DE CÁLCULO CUANTITATIVA (M$) — 10 FILAS DE TRAZABILIDAD
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
        tope_cpt = mem.get("tope_patrimonial_12pct_cpt") or mem.get("tope_patrimonial_cpt")
        cupo_max = mem.get("linea_maxima_condicionada") or mem.get("cupo_maximo_sugerido", 0)
        cupo_ini = mem.get("linea_inicial_sugerida") or linea_ini
        pct_ap = mem.get("pct_apertura_inicial", 50)

        rango_str = f" ({p_ini} a {p_fin})" if p_ini and p_fin else ""
        cpt_str = format_mclp(cpt_val) if cpt_val is not None else "Sin F22"

        if rli_mens and rli_mens > 0:
            metodologia_b2 = "min(15% Spread Operacional F29, 25% RLI Mensualizada F22)"
        else:
            metodologia_b2 = "12% Spread Operacional F29 (penalizado por RLI no disponible o <= 0)"

        mem_rows = [
            [
                Paragraph("<b>Paso de Memoria Cuantitativa</b>", table_cell_header),
                Paragraph("<b>Metodología / Fundamento Operacional</b>", table_cell_header),
                Paragraph("<b>Monto (M$)</b>", table_cell_header),
            ],
            [
                Paragraph(f"Ventas Netas Mensuales Promedio{rango_str}", table_cell_bold),
                Paragraph("Promedio mensual ventas de los 12 meses analizados", table_cell),
                Paragraph(format_mclp(v_prom), table_cell_bold),
            ],
            [
                Paragraph("(-) Paso A: Compras Op. Mensuales Promedio (C_base)", table_cell_bold),
                Paragraph("Base mensual de compras operacionales 12M (o costo proxy)", table_cell),
                Paragraph(format_mclp(base_c), table_cell_bold),
            ],
            [
                Paragraph("(=) Spread Operacional Tributario F29", table_cell_bold),
                Paragraph("Ventas Netas Mensuales Promedio − Compras Op. Mensuales Promedio", table_cell),
                Paragraph(format_mclp(spread_f29), table_cell_bold),
            ],
            [
                Paragraph("Paso B1: Techo por Volumen de Compras (8% C_base)", table_cell_bold),
                Paragraph("8% sobre C_base (parámetro prudencial de exposición por proveedor: 8% C_base)", table_cell),
                Paragraph(format_mclp(techo_op), table_cell_bold),
            ],
            [
                Paragraph("Paso B2: Freno por Absorción Operacional", table_cell_bold),
                Paragraph(metodologia_b2, table_cell),
                Paragraph(format_mclp(freno_flujo), table_cell_bold),
            ],
            [
                Paragraph("Paso C: Factor de Ajuste Conductual", table_cell_bold),
                Paragraph("Ajuste por mora F29, postergación IVA y estabilidad YoY", table_cell),
                Paragraph(f"{phi_pct}%", table_cell_bold),
            ],
            [
                Paragraph(f"Paso D: Referencia Patrimonial (12% CPT = {cpt_str})", table_cell_bold),
                Paragraph("12% CPT en línea limpia ($0 si CPT <= 0)", table_cell),
                Paragraph(format_mclp(tope_cpt) if tope_cpt is not None else "Sin tope", table_cell_bold),
            ],
            [
                Paragraph("(=) Línea Máxima Condicionada (Techo Técnico)", table_cell_bold),
                Paragraph("min(Techo 8%, Freno Absorción) × Factor Conductual con Tope CPT (M$ 100)", table_cell),
                Paragraph(format_mclp(cupo_max), table_cell_bold),
            ],
            [
                Paragraph(f"(=) Línea Inicial Recomendada (Etapa 1 - {pct_ap}% Apertura)", table_cell_bold),
                Paragraph(f"{pct_ap}% de la Línea Máxima Técnica según Puntaje SII", table_cell),
                Paragraph(format_mclp(cupo_ini), table_cell_bold),
            ],
        ]
        mem_table = Table(mem_rows, colWidths=[70 * mm, 85 * mm, 30 * mm])
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
                ("BACKGROUND", (0, 9), (-1, 9), colors.HexColor("#FEF3C7")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 1.6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
                ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ])
        )
        story.append(Paragraph("Memoria de Cálculo Cuantitativa de Línea Comercial (M$)", h2_style))
        story.append(mem_table)
        story.append(Spacer(1, 2 * mm))

        # 6. CONDICIONES SUSPENSIVAS, ALERTAS Y MONITOREO SUGERIDO (RECUADRO LIMPIO)
        banderas = getattr(cr, "banderas_rojas", []) if cr else []
        cond_escalamiento = getattr(cr, "condicion_escalamiento", None) or (
            "Habilitable tras 2 a 3 ciclos de pago completos y oportunos, sujeta a Dicom/Equifax sin morosidad "
            "vigente, constitución de resguardo (pagaré a la vista / seguro de crédito) y validación de estados financieros."
        )

        alertas_p = [
            Paragraph("<b>Condiciones Suspensivas y Alertas Críticas:</b>", table_cell_bold),
        ]
        if banderas:
            for b in banderas:
                alertas_p.append(Paragraph(f"• <b>Alerta:</b> {b}", body_style))
        else:
            alertas_p.append(Paragraph("• 🟢 <i>Sin alertas críticas detectadas en declaraciones tributarias.</i>", body_style))

        alertas_p.append(Spacer(1, 1 * mm))
        alertas_p.append(Paragraph(f"• <b>Boletín Comercial Dicom/Equifax:</b> {boletin_com}", body_style))
        alertas_p.append(Paragraph(f"• <b>Historial con Proveedor:</b> {hist_pago}", body_style))

        control_p = [
            Paragraph("<b>Escalamiento Comercial y Monitoreo Sugerido:</b>", table_cell_bold),
            Paragraph(f"• <b>Condición de Escalamiento (Paso a Línea Máxima):</b> {cond_escalamiento}", body_style),
            Paragraph("• <b>Monitoreo Durante Primeros 90 Días:</b> Revisión mensual obligatoria de cumplimiento en pagos y vigencia de declaraciones F29 antes de cada despacho.", body_style),
            Paragraph(f"• <b>Resguardo Previo al Despacho:</b> {resguardo}", body_style),
        ]

        flags_table = Table([[alertas_p, control_p]], colWidths=[92.5 * mm, 92.5 * mm])
        flags_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        story.append(Paragraph("Condiciones Suspensivas, Alertas y Monitoreo Sugerido", h2_style))
        story.append(flags_table)
        story.append(Spacer(1, 2.5 * mm))

        # 7. TABLA RESUMEN F29 (Últimos 12 meses cronológicos en M$)
        monthly_taxes = getattr(tax_folder, "monthly_taxes", []) or []
        if monthly_taxes:
            sorted_mt = sorted(monthly_taxes, key=lambda m: m.periodo or "")
            last_12_mt = sorted_mt[-12:] if len(sorted_mt) >= 12 else sorted_mt
            mes_inicio = last_12_mt[0].periodo if last_12_mt else ""
            mes_fin = last_12_mt[-1].periodo if last_12_mt else ""

            f29_header = [
                Paragraph("<b>Período</b>", table_cell_header),
                Paragraph("<b>Ventas Netas (M$)</b>", table_cell_header),
                Paragraph("<b>Compras Op. (M$)</b>", table_cell_header),
                Paragraph("<b>Débito Fiscal (M$)</b>", table_cell_header),
                Paragraph("<b>Crédito Fiscal (M$)</b>", table_cell_header),
                Paragraph("<b>IVA Det. SII (M$)</b>", table_cell_header),
            ]
            f29_rows = [f29_header]

            tot_v = Decimal("0")
            tot_cop = Decimal("0")
            tot_deb = Decimal("0")
            tot_cred = Decimal("0")
            tot_iva = Decimal("0")

            for mt in last_12_mt:
                v = mt.total_ventas or Decimal("0")
                cop = mt.compras_operacionales if mt.compras_operacionales is not None else (mt.compras or Decimal("0"))
                deb = mt.debito_fiscal or Decimal("0")
                cred = mt.credito_fiscal or Decimal("0")
                iva = mt.iva_determinado or Decimal("0")

                tot_v += v
                tot_cop += cop
                tot_deb += deb
                tot_cred += cred
                tot_iva += iva

                f29_rows.append([
                    Paragraph(getattr(mt, "periodo", ""), table_cell),
                    Paragraph(format_mclp(v), table_cell),
                    Paragraph(format_mclp(cop), table_cell),
                    Paragraph(format_mclp(deb), table_cell),
                    Paragraph(format_mclp(cred), table_cell),
                    Paragraph(format_mclp(iva), table_cell),
                ])

            n_12 = Decimal(str(len(last_12_mt))) if last_12_mt else Decimal("1")
            prom_v_row = tot_v / n_12
            prom_cop_row = base_c  # Coincide matemáticamente con Paso A C_base
            prom_deb_row = tot_deb / n_12
            prom_cred_row = tot_cred / n_12
            prom_iva_row = tot_iva / n_12

            # Fila de Promedio Mensual (12M)
            f29_rows.append([
                Paragraph("<b>Promedio Mensual (12M)</b>", table_cell_bold),
                Paragraph(format_mclp(prom_v_row), table_cell_bold),
                Paragraph(format_mclp(prom_cop_row), table_cell_bold),
                Paragraph(format_mclp(prom_deb_row), table_cell_bold),
                Paragraph(format_mclp(prom_cred_row), table_cell_bold),
                Paragraph(format_mclp(prom_iva_row), table_cell_bold),
            ])

            # Fila de Total Acumulado (12M)
            f29_rows.append([
                Paragraph("<b>Total Acumulado (12M)</b>", table_cell_bold),
                Paragraph(format_mclp(tot_v), table_cell_bold),
                Paragraph(format_mclp(tot_cop), table_cell_bold),
                Paragraph(format_mclp(tot_deb), table_cell_bold),
                Paragraph(format_mclp(tot_cred), table_cell_bold),
                Paragraph(format_mclp(tot_iva), table_cell_bold),
            ])

            f29_table = Table(f29_rows, colWidths=[25 * mm, 32 * mm, 32 * mm, 32 * mm, 32 * mm, 32 * mm])
            f29_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                    ("BACKGROUND", (0, -2), (-1, -2), colors.HexColor("#F1F5F9")),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E2E8F0")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ])
            )
            story.append(KeepTogether([
                Paragraph(f"Resumen F29 — Período Analizado: {mes_inicio} a {mes_fin} (Últimos 12 Meses Declarados)", h2_style),
                f29_table,
            ]))

        # 8. TABLA RESUMEN F22 Y CONCILIACIÓN CRUZADA (M$)
        f22_list = getattr(tax_folder, "f22", []) or []
        if f22_list:
            sorted_f22 = sorted(f22_list, key=lambda f: f.anio_tributario or "", reverse=True)
            story.append(Spacer(1, 2 * mm))
            f22_header = [
                Paragraph("<b>Año Tributario</b>", table_cell_header),
                Paragraph("<b>Ingresos Anuales (M$)</b>", table_cell_header),
                Paragraph("<b>RLI (M$)</b>", table_cell_header),
                Paragraph("<b>Capital Propio CPT (M$)</b>", table_cell_header),
            ]
            f22_rows = [f22_header]
            for f in sorted_f22[:3]:
                ing = getattr(f, "ingresos", None)
                rli = getattr(f, "renta_liquida_imponible", None)
                cpt_f = getattr(f, "capital_propio_tributario", None)
                anio_clean = str(getattr(f, "anio_tributario", "")).replace(":", "").strip()
                f22_rows.append([
                    Paragraph(anio_clean, table_cell),
                    Paragraph(format_mclp(ing).replace(":", "").strip(), table_cell),
                    Paragraph(format_mclp(rli).replace(":", "").strip(), table_cell),
                    Paragraph(format_mclp(cpt_f).replace(":", "").strip(), table_cell),
                ])
            f22_table = Table(f22_rows, colWidths=[30 * mm, 50 * mm, 50 * mm, 55 * mm])
            f22_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ])
            )
            story.append(KeepTogether([
                Paragraph("Resumen de Declaraciones Anuales F22 (Patrimonio e Impuesto a la Renta en M$)", h2_style),
                f22_table,
            ]))

        # Conciliación Cruzada F29 vs F22
        conciliacion = getattr(cr, "conciliacion_f29_f22", None)
        if conciliacion:
            story.append(Spacer(1, 1.5 * mm))
            conc_text = (
                f"<b>Conciliación Cruzada F29 vs F22:</b> {conciliacion.get('detalle', '')}"
            )
            story.append(Paragraph(conc_text, body_style))

        # Footer nota M$ y nota legal
        story.append(Spacer(1, 2.5 * mm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=2))
        nota_pie = (
            "<i>Nota Legal: Cifras expresadas en Miles de Pesos Chilenos (M$). "
            "Este informe constituye una recomendación cuantitativa referencial y no vinculante basada en declaraciones tributarias SII; "
            "la decisión final de otorgamiento de crédito es de exclusiva responsabilidad del proveedor.</i>"
        )
        story.append(Paragraph(nota_pie, ParagraphStyle("NotaPie", parent=body_style, fontSize=6.5, leading=8.5, textColor=colors.HexColor("#64748B"))))

        doc.build(story)
        return buffer.getvalue()
