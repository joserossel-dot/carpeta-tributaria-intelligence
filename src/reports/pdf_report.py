import datetime
import io
import re
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
                "Informe Cuantitativo Referencial para Otorgamiento de Crédito Comercial B2B (v2.9.0)",
                subtitle_style,
            )
        )
        story.append(Spacer(1, 2 * mm))

        # 2. IDENTIFICACIÓN DEL CONTRIBUYENTE Y VIGENCIA
        c = getattr(tax_folder, "contributor", None)
        kpis = getattr(tax_folder, "kpis", None)
        cr = getattr(tax_folder, "credit_risk", None)
        forma_act = getattr(tax_folder.corporate, "forma_actuacion_representantes", None) if getattr(tax_folder, "corporate", None) else None

        rut = getattr(c, "rut", None) or "No informado"
        razon_social = getattr(c, "razon_social", None) or "No informada"
        domicilio_raw = getattr(c, "domicilio", None) or "No informado"
        domicilio = (
            re.sub(r"(\d)([a-zA-ZáéíóúñÁÉÍÓÚÑ])", r"\1 \2", domicilio_raw)
            if domicilio_raw != "No informado"
            else domicilio_raw
        )
        comuna_str = (getattr(c, "comuna", None) or "").strip()
        region_str = (getattr(c, "region", None) or "").strip()
        if comuna_str and region_str and region_str not in ("—", "-", "None"):
            comuna_region = f"{comuna_str}, {region_str}"
        elif comuna_str:
            comuna_region = comuna_str
        elif region_str and region_str not in ("—", "-", "None"):
            comuna_region = region_str
        else:
            comuna_region = "—"
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
                Paragraph(f"<b>Emisión Carpeta SII:</b> {fecha_emision} | <b>Último F29:</b> {ult_periodo} | <b>Desfase al Emitir:</b> {desfase_m}m", body_style),
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
        desempeno_texto = getattr(cr, "desempeno_tributario_texto", None) or ("Capacidad Operativa Tributaria Alta" if score_val >= 80 else "Desempeño Tributario Medio")
        linea_ini = getattr(cr, "linea_inicial_sugerida", 0) if cr else 0
        linea_max = getattr(cr, "linea_maxima_condicionada", 0) or getattr(cr, "cupo_maximo_sugerido", 0) if cr else 0
        plazo_dias = getattr(cr, "plazo_sugerido_dias", 0) if cr else 0
        plazo_ini = getattr(cr, "plazo_inicial_sugerido", None) or (f"{plazo_dias} días" if plazo_dias > 0 else "Contado")
        resguardo = getattr(cr, "resguardo_comercial_sugerido", None) or getattr(cr, "garantia_exigida", "Venta al contado") if cr else "Venta al contado"

        # Color de la evaluación referencial
        if "ELEGIBLE" in evaluacion or "SÓLIDO" in evaluacion or "SOLIDO" in evaluacion or "BAJO" in evaluacion:
            badge_bg = colors.HexColor("#16A34A")
        elif "MODERADO" in evaluacion or "MEDIO" in evaluacion:
            badge_bg = colors.HexColor("#D97706")
        elif "ACOTADO" in evaluacion or "CONDICIONES" in evaluacion:
            badge_bg = colors.HexColor("#EA580C")
        elif "DÉBIL" in evaluacion or "DEBIL" in evaluacion or "ALTO" in evaluacion or "RECHAZADO" in evaluacion:
            badge_bg = colors.HexColor("#DC2626")
        else:
            badge_bg = colors.HexColor("#475569")

        evaluacion_cell = Paragraph(f"<b>{evaluacion}</b><br/><font size=5.0 color='#FFFFFF'>No constituye rating de solvencia ni mide endeudamiento financiero; sujeto a Dicom y Balance</font>", badge_style)
        linea_ini_txt = format_mclp(linea_ini)
        linea_max_txt = format_mclp(linea_max)

        resguardo_style = ParagraphStyle(
            "ResguardoStyle",
            parent=table_cell,
            fontName="Helvetica",
            fontSize=6.8,
            leading=8.2,
            textColor=colors.HexColor("#1E293B"),
        )

        reps_list = getattr(tax_folder.corporate, "representantes", []) if getattr(tax_folder, "corporate", None) else []
        n_reps = len(reps_list)
        forma_act = getattr(tax_folder.corporate, "forma_actuacion_representantes", None) if getattr(tax_folder, "corporate", None) else None
        act_txt = f"Actuación SII: {forma_act} — " if forma_act else ""

        if linea_ini > 0:
            resguardo_box_txt = (
                f"<b>Plazo Inicial:</b> {plazo_ini}. Línea no liberable sin: "
                "(1) Dicom/Equifax sin morosidad vigente, y "
                "(2) Pagaré notarial suscrito según estatutos vigentes acreditados en escritura social o certificado de vigencia de poderes del CBR/Registro Electrónico (la actuación ante el SII no sustituye el mandato mercantil de administración) o Seguro de Crédito; "
                "o esquema mixto (50% anticipo + 50% a 30 días)."
            )
        else:
            resguardo_box_txt = f"<b>Plazo Inicial:</b> {plazo_ini}.<br/>{resguardo}"

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
                Paragraph(resguardo_box_txt, resguardo_style),
            ],
        ]
        panel_table = Table(panel_data, colWidths=[52 * mm, 37 * mm, 37 * mm, 59 * mm])
        panel_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("BACKGROUND", (0, 1), (0, 1), badge_bg),
                ("BACKGROUND", (1, 1), (-1, 1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0F172A")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2.0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.0),
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
        tope_cpt = mem.get("tope_patrimonial_3pct_cpt") or mem.get("tope_patrimonial_12pct_cpt") or mem.get("tope_patrimonial_cpt")
        cupo_max = mem.get("linea_maxima_condicionada") or mem.get("cupo_maximo_sugerido", 0)
        cupo_ini = mem.get("linea_inicial_sugerida") or linea_ini
        pct_ap = mem.get("pct_apertura_inicial", 50)

        rango_str = f" ({p_ini} a {p_fin})" if p_ini and p_fin else ""
        cpt_str = format_mclp(cpt_val) if cpt_val is not None else "Sin F22"

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
            cpt_code_d = mem.get("cpt_source_code") or (tax_folder.f22[0].cpt_source_code if tax_folder.f22 and getattr(tax_folder.f22[0], "cpt_source_code", None) else "645")
            cpt_tipo_d = "CPTS" if cpt_code_d in ("1545", "1546", "1584", "1585") else "CPT"
            glosa_d = mem.get("glosa_paso_d") or f"Bloqueo por {cpt_tipo_d} Negativo en F22 (Cód. {cpt_code_d}: {format_mclp(cpt_val)} -> Tope Patrimonial M$ 0)"
            monto_d = "M$ 0"
        elif tope_cpt is not None:
            glosa_d = mem.get("glosa_paso_d") or "Tope de concentración por proveedor: 3% CPT; actúa como freno en empresas subcapitalizadas o con CPT <= 0"
            monto_d = format_mclp(tope_cpt)
        else:
            glosa_d = "Sin F22 vigente"
            monto_d = "Sin tope"

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
                Paragraph("Ventas Netas Mensuales Promedio - Compras Op. Mensuales Promedio", table_cell),
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
                Paragraph(
                    mem.get("glosa_paso_c")
                    or f"Tramo Score {'>=85' if score_val >= 85 else ('75-84' if score_val >= 75 else ('65-74' if score_val >= 65 else '<65'))}: {phi_pct}% (Escala: >=85: 100% | 75-84: 80% | 65-74: 60% | <65: 0%)",
                    table_cell,
                ),
                Paragraph(f"{phi_pct}%", table_cell_bold),
            ],
            [
                Paragraph(f"Paso D: Referencia Patrimonial (3% CPT = {cpt_str})", table_cell_bold),
                Paragraph(glosa_d, table_cell),
                Paragraph(monto_d, table_cell_bold),
            ],
            [
                Paragraph("(=) Línea Máxima Condicionada (Techo Técnico)", table_cell_bold),
                Paragraph("min(Techo 8%, Freno Absorción) x Factor Conductual con Tope CPT (truncado a múltiplos de M$ 100)", table_cell),
                Paragraph(format_mclp(cupo_max), table_cell_bold),
            ],
            [
                Paragraph(f"(=) Línea Inicial Recomendada (Etapa 1 - {pct_ap}% Apertura)", table_cell_bold),
                Paragraph(
                    mem.get("glosa_apertura")
                    or f"{pct_ap}% de Apertura para Score {'>=85' if score_val >= 85 else ('75-84' if score_val >= 75 else ('65-74' if score_val >= 65 else '<65'))} (Escala: >=85: 50% | 75-84: 40% | 65-74: 30% | <65: 0%)",
                    table_cell,
                ),
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

        # Verificación de antigüedad de emisión de carpeta
        dias_emision = None
        if fecha_emision and fecha_emision != "No informada":
            try:
                date_part = str(fecha_emision).strip().split()[0]
                d, m, y = 0, 0, 0
                if "/" in date_part:
                    p = date_part.split("/")
                    if len(p) == 3:
                        d, m, y = int(p[0]), int(p[1]), int(p[2])
                elif "-" in date_part:
                    p = date_part.split("-")
                    if len(p) == 3:
                        if len(p[0]) == 4:
                            y, m, d = int(p[0]), int(p[1]), int(p[2])
                        else:
                            d, m, y = int(p[0]), int(p[1]), int(p[2])
                if y > 0 and m > 0 and d > 0:
                    fecha_dt = datetime.date(y, m, d)
                    hoy = datetime.date.today()
                    dias_emision = (hoy - fecha_dt).days
            except Exception:
                pass

        alertas_p = [
            Paragraph("<b>Condiciones Suspensivas y Alertas Críticas:</b>", table_cell_bold),
        ]
        if banderas:
            for b in banderas:
                alertas_p.append(Paragraph(f"• <b>Alerta:</b> {b}", body_style))
        else:
            alertas_p.append(Paragraph("• 🟢 <i>Sin alertas críticas detectadas en declaraciones tributarias.</i>", body_style))

        if dias_emision is not None and dias_emision > 45:
            alertas_p.append(
                Paragraph(
                    f"• <b>Condición Suspensiva de Vigencia:</b> Carpeta emitida hace {dias_emision} días (> 45 días). "
                    "Se exige actualización de carpeta tributaria antes del desembolso si supera 60 días.",
                    body_style,
                )
            )

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
        story.append(KeepTogether([
            Paragraph("Condiciones Suspensivas, Alertas y Monitoreo Sugerido", h2_style),
            flags_table,
        ]))
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
                Paragraph("<b>Crédito Giro Mes (M$)</b>", table_cell_header),
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
                cred = mt.credito_operacional if mt.credito_operacional is not None else (mt.credito_fiscal or Decimal("0"))
                iva = mt.iva_determinado or Decimal("0")

                tot_v += v
                tot_cop += cop
                tot_deb += deb
                tot_cred += cred
                tot_iva += iva

                f29_rows.append([
                    Paragraph(getattr(mt, "periodo", ""), table_cell),
                    Paragraph(format_mclp(v).replace(" ", "&nbsp;"), table_cell),
                    Paragraph(format_mclp(cop).replace(" ", "&nbsp;"), table_cell),
                    Paragraph(format_mclp(deb).replace(" ", "&nbsp;"), table_cell),
                    Paragraph(format_mclp(cred).replace(" ", "&nbsp;"), table_cell),
                    Paragraph(format_mclp(iva).replace(" ", "&nbsp;"), table_cell),
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
                Paragraph(format_mclp(prom_v_row).replace(" ", "&nbsp;"), table_cell_bold),
                Paragraph(format_mclp(prom_cop_row).replace(" ", "&nbsp;"), table_cell_bold),
                Paragraph(format_mclp(prom_deb_row).replace(" ", "&nbsp;"), table_cell_bold),
                Paragraph(format_mclp(prom_cred_row).replace(" ", "&nbsp;"), table_cell_bold),
                Paragraph(format_mclp(prom_iva_row).replace(" ", "&nbsp;"), table_cell_bold),
            ])

            # Fila de Total Acumulado (12M)
            f29_rows.append([
                Paragraph("<b>Total Acumulado (12M)</b>", table_cell_bold),
                Paragraph(format_mclp(tot_v).replace(" ", "&nbsp;"), table_cell_bold),
                Paragraph(format_mclp(tot_cop).replace(" ", "&nbsp;"), table_cell_bold),
                Paragraph(format_mclp(tot_deb).replace(" ", "&nbsp;"), table_cell_bold),
                Paragraph(format_mclp(tot_cred).replace(" ", "&nbsp;"), table_cell_bold),
                Paragraph(format_mclp(tot_iva).replace(" ", "&nbsp;"), table_cell_bold),
            ])

            f29_table = Table(f29_rows, colWidths=[22 * mm, 32.6 * mm, 32.6 * mm, 32.6 * mm, 32.6 * mm, 32.6 * mm])
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
            n_at = len(sorted_f22[:3])
            at_plural = "s" if n_at > 1 else ""
            f22_titulo = f"Resumen de Declaraciones Anuales F22 ({n_at} AT contenido{at_plural} en carpeta SII — Ingresos, RLI y CPT en M$)"
            regimen = getattr(getattr(tax_folder, "contributor", None), "regimen_tributario", "") or ""
            is_14d8 = any(getattr(f, "ingresos_source_code", None) == "1600" or getattr(f, "rli_source_code", None) in ("1626", "1627") or getattr(f, "cpt_source_code", None) in ("1584", "1585") for f in sorted_f22) or any(k in regimen.upper() for k in ("14 D N° 8", "14D8", "14 D) Nº 8", "14D N°8", "TRANSPARENTE"))
            is_14d3 = not is_14d8 and (any(getattr(f, "ingresos_source_code", None) in ("1400", "1410") or getattr(f, "rli_source_code", None) in ("1440", "1450") or getattr(f, "cpt_source_code", None) in ("1545", "1546") for f in sorted_f22) or any(k in regimen.upper() for k in ("14 D N° 3", "14D3", "14 D) Nº 3", "14D N°3", "PRO PYME GENERAL", "PRO PYME")))

            if is_14d8:
                col2_head = "Ingresos Giro Cód. 1600 (M$)"
                col3_head = "Base Imponible / Pérdida Cód. 1626/1627 (M$)"
                col4_head = "Capital Propio CPTS Cód. 1584/1585 (M$)"
            elif is_14d3:
                col2_head = "Ingresos Giro Cód. 1400 (M$)"
                col3_head = "Base Imponible / Pérdida Cód. 1440/1450 (M$)"
                col4_head = "Capital Propio CPTS Cód. 1545/1546 (M$)"
            else:
                col2_head = "Ingresos Giro Cód. 1657 (M$)"
                col3_head = "RLI / Pérdida Cód. 1694/1695 (M$)"
                col4_head = "Capital Propio CPT Cód. 645/1698 (M$)"

            f22_header = [
                Paragraph("<b>Año Tributario</b>", table_cell_header),
                Paragraph(f"<b>{col2_head}</b>", table_cell_header),
                Paragraph(f"<b>{col3_head}</b>", table_cell_header),
                Paragraph(f"<b>{col4_head}</b>", table_cell_header),
            ]
            f22_rows = [f22_header]
            for f in sorted_f22[:3]:
                ing = getattr(f, "ingresos", None)
                rli = getattr(f, "renta_liquida_imponible", None)
                cpt_f = getattr(f, "capital_propio_tributario", None)
                anio_clean = str(getattr(f, "anio_tributario", "")).replace(":", "").strip()

                ing_code = getattr(f, "ingresos_source_code", None)
                ing_fmt = format_mclp(ing).replace(":", "").strip()
                if ing_code and ing_fmt != "—":
                    if is_14d3 and ing_code != "1400":
                        ing_cell_txt = f"{ing_fmt} (Cód. {ing_code})"
                    elif is_14d8 and ing_code != "1600":
                        ing_cell_txt = f"{ing_fmt} (Cód. {ing_code})"
                    elif not is_14d3 and not is_14d8 and ing_code != "1657":
                        ing_cell_txt = f"{ing_fmt} (Cód. {ing_code})"
                    else:
                        ing_cell_txt = ing_fmt
                else:
                    ing_cell_txt = ing_fmt

                rli_code = getattr(f, "rli_source_code", None)
                if not rli_code:
                    rli_code = "1695" if (rli is not None and rli < 0) else "1694"
                rli_fmt = format_mclp(rli).replace(":", "").strip()
                rli_cell_txt = f"{rli_fmt} (Cód. {rli_code})" if (rli is not None and rli_fmt != "—") else rli_fmt

                cpt_code = getattr(f, "cpt_source_code", None)
                cpt_fmt = format_mclp(cpt_f).replace(":", "").strip()
                if cpt_code and cpt_fmt != "—":
                    if is_14d3 and cpt_code in ("1545", "1546", "645", "646"):
                        cpt_cell_txt = f"{cpt_fmt} (Cód. {cpt_code})"
                    elif is_14d8 and cpt_code in ("1584", "1585", "645", "646"):
                        cpt_cell_txt = f"{cpt_fmt} (Cód. {cpt_code})"
                    elif cpt_code in ("1545", "1546", "1584", "1585"):
                        cpt_cell_txt = f"{cpt_fmt} (Cód. {cpt_code})"
                    else:
                        cpt_cell_txt = cpt_fmt
                else:
                    cpt_cell_txt = cpt_fmt

                f22_rows.append([
                    Paragraph(anio_clean, table_cell),
                    Paragraph(ing_cell_txt, table_cell),
                    Paragraph(rli_cell_txt, table_cell),
                    Paragraph(cpt_cell_txt, table_cell),
                ])
            f22_table = Table(f22_rows, colWidths=[28 * mm, 50 * mm, 58 * mm, 49 * mm])
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
                Paragraph(f22_titulo, h2_style),
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
            "la decisión final de otorgamiento de crédito es de exclusiva responsabilidad del proveedor. "
            "[Motor Determinista Cavilaria v2.9.0 | Política Base: B1=8% Compras, B2=min(15% Spread F29, 25% RLI/12; RLI<=0 -> M$ 0; sin F22 -> 8% Spread), C=100%/80%/60%/0%, D=3% CPT (CPT<=0 -> M$ 0), Apertura=50%/40%/30%/0%]</i>"
        )
        story.append(Paragraph(nota_pie, ParagraphStyle("NotaPie", parent=body_style, fontSize=6.5, leading=8.5, textColor=colors.HexColor("#64748B"))))

        doc.build(story)
        return buffer.getvalue()
