#!/usr/bin/env python3
"""
Script de auditoría y verificación cuantitativa del Motor de Comité de Crédito B2B v2.0.
Evalúa todas las carpetas tributarias de examples/ con un cupo solicitado de $35.000.000.
Genera la tabla comparativa y el informe RESULTADOS_COMITE_V2.md.
"""

from decimal import Decimal
import json
from pathlib import Path
import sys

from src.core.tax_folder_engine import TaxFolderEngine


def fmt_pesos(val: int | float | Decimal | None) -> str:
    if val is None:
        return "N/D"
    try:
        return f"${int(round(float(val))):,.0f}".replace(",", ".")
    except Exception:
        return str(val)


def main() -> None:
    examples_dir = Path("examples")
    pdf_files = sorted(examples_dir.glob("*.pdf"))

    print(f"=== Auditoría Comité de Crédito B2B v2.0 ===")
    print(f"Encontrados {len(pdf_files)} archivos PDF en {examples_dir}\n")

    cupo_solicitado = 35_000_000
    casos = []

    for pdf in pdf_files:
        print(f"Procesando: {pdf.name} ...", end=" ", flush=True)
        try:
            engine = TaxFolderEngine(str(pdf))
            tf = engine.parse(cupo_solicitado=cupo_solicitado)
            
            c = tf.contributor
            rut = c.rut if c and c.rut else "N/D"
            razon_social = c.razon_social if c and c.razon_social else "N/D"
            regimen = c.regimen_tributario if c and c.regimen_tributario else "Sin Régimen Informado"
            
            act_p = "N/D"
            if tf.activities:
                p_acts = [a for a in tf.activities if a.principal]
                if p_acts:
                    act_p = f"{p_acts[0].codigo} - {p_acts[0].descripcion}"
                else:
                    act_p = f"{tf.activities[0].codigo} - {tf.activities[0].descripcion}"

            ma = tf.monthly_analysis
            ventas_12m = ma.ventas_ultimos_12 if ma else None
            compras_op_12m = None
            if ma:
                if ma.promedio_compras_operacionales_12m:
                    compras_op_12m = ma.promedio_compras_operacionales_12m * 12
                elif ma.compras_ultimos_12:
                    compras_op_12m = ma.compras_ultimos_12

            # CPT más reciente
            cpt_val = None
            cpt_anio = None
            if tf.f22:
                f22_cpt = sorted([f for f in tf.f22 if f.capital_propio_tributario is not None], key=lambda x: x.anio_tributario or "", reverse=True)
                if f22_cpt:
                    cpt_val = f22_cpt[0].capital_propio_tributario
                    cpt_anio = f22_cpt[0].anio_tributario

            cr = tf.credit_risk
            if cr:
                veredicto = cr.veredicto
                score = cr.score_crediticio
                cat_riesgo = cr.categoria_riesgo
                cupo_max = cr.cupo_maximo_sugerido
                cupo_aprob = cr.cupo_aprobado
                plazo = cr.plazo_sugerido_dias
                garantia = cr.garantia_exigida
                dictamen = cr.dictamen_ejecutivo
                banderas = cr.banderas_rojas
                hoja_ruta = cr.hoja_ruta_comercial
                mc = cr.memoria_calculo or {}
                
                # Indicadores
                score_mora = cr.indicadores.mora_efectiva.score
                score_margen = cr.indicadores.margen_vs_giro.score
                score_respaldo = cr.indicadores.respaldo_estructural.score
            else:
                veredicto = "ERROR_MOTOR"
                score = 0.0
                cat_riesgo = "N/D"
                cupo_max = 0
                cupo_aprob = 0
                plazo = 0
                garantia = "N/D"
                dictamen = "Error al ejecutar el motor de riesgo"
                banderas = []
                hoja_ruta = []
                mc = {}
                score_mora = None
                score_margen = None
                score_respaldo = None

            caso = {
                "archivo": pdf.name,
                "rut": rut,
                "razon_social": razon_social,
                "regimen": regimen,
                "actividad": act_p,
                "ventas_12m": ventas_12m,
                "compras_op_12m": compras_op_12m,
                "cpt": cpt_val,
                "cpt_anio": cpt_anio,
                "veredicto": veredicto,
                "score": score,
                "cat_riesgo": cat_riesgo,
                "score_mora": score_mora,
                "score_margen": score_margen,
                "score_respaldo": score_respaldo,
                "cupo_maximo": cupo_max,
                "cupo_solicitado": cupo_solicitado,
                "cupo_aprobado": cupo_aprob,
                "plazo_dias": plazo,
                "garantia": garantia,
                "dictamen": dictamen,
                "banderas_rojas": banderas,
                "hoja_ruta": hoja_ruta,
                "memoria_calculo": mc,
                "meses_f29": len(tf.monthly_taxes),
                "num_f22": len(tf.f22),
            }
            casos.append(caso)
            print(f"OK -> Veredicto: {veredicto} | Score: {score:.1f} | Cupo Aprobado: {fmt_pesos(cupo_aprob)}")
        except Exception as e:
            print(f"FALLO: {e}")
            casos.append({
                "archivo": pdf.name,
                "rut": "ERROR",
                "razon_social": f"Error: {e}",
                "regimen": "N/D",
                "actividad": "N/D",
                "ventas_12m": None,
                "compras_op_12m": None,
                "cpt": None,
                "cpt_anio": None,
                "veredicto": "NO_EVALUABLE",
                "score": 0.0,
                "cat_riesgo": "N/D",
                "score_mora": None,
                "score_margen": None,
                "score_respaldo": None,
                "cupo_maximo": 0,
                "cupo_solicitado": cupo_solicitado,
                "cupo_aprobado": 0,
                "plazo_dias": 0,
                "garantia": "N/D",
                "dictamen": str(e),
                "banderas_rojas": [f"Error de procesamiento: {e}"],
                "hoja_ruta": [],
                "memoria_calculo": {},
                "meses_f29": 0,
                "num_f22": 0,
            })

    # Generar Markdown
    md = []
    md.append("# RESULTADOS COMITÉ DE CRÉDITO B2B v2.0\n")
    md.append("## Simulación Masiva y Asignación de Cupo Comercial")
    md.append(f"**Parámetro de Ensayo:** Cupo Comercial Solicitado = **{fmt_pesos(cupo_solicitado)}** (30 días de plazo)\n")
    md.append("---")
    md.append("### 1. Cuadro Resumen Ejecutivo Multicartera\n")

    headers = [
        "Archivo / RUT",
        "Régimen / Actividad",
        "Ventas 12M",
        "Compras Op 12M",
        "CPT",
        "Veredicto v2.0",
        "Score (M/Mg/R)",
        "Cupo Máx Sugerido",
        "Cupo Aprobado",
        "Plazo / Garantía",
    ]
    md.append("| " + " | ".join(headers) + " |")
    md.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for c in casos:
        rut_nom = f"**{c['archivo']}**<br>`{c['rut']}`<br>*{c['razon_social'][:25]}*"
        reg_act = f"{c['regimen'][:22]}...<br>*{c['actividad'][:30]}*"
        v12 = fmt_pesos(c['ventas_12m'])
        cop12 = fmt_pesos(c['compras_op_12m'])
        cpt_str = f"{fmt_pesos(c['cpt'])} ({c['cpt_anio']})" if c['cpt'] is not None else "Sin F22 CPT"
        
        ver_badge = c['veredicto']
        if "APROBADO" in ver_badge and "CONDICIONES" not in ver_badge:
            ver_badge = f"🟢 **{ver_badge}**"
        elif "CONDICIONES" in ver_badge or "OBSERVADO" in ver_badge:
            ver_badge = f"🟡 **{ver_badge}**"
        else:
            ver_badge = f"🔴 **{ver_badge}**"

        score_detail = f"**{c['score']:.1f}**<br>({c['score_mora'] or '-'}/{c['score_margen'] or '-'}/{c['score_respaldo'] or '-'})"
        cupo_max_str = fmt_pesos(c['cupo_maximo'])
        cupo_aprob_str = f"**{fmt_pesos(c['cupo_aprobado'])}**"
        gar_txt = str(c['garantia'])[:28] if c['garantia'] else "Sin garantía exigida"
        plazo_gar = f"{c['plazo_dias'] or 0} días<br>*{gar_txt}*"

        row = [
            rut_nom,
            reg_act,
            v12,
            cop12,
            cpt_str,
            ver_badge,
            score_detail,
            cupo_max_str,
            cupo_aprob_str,
            plazo_gar,
        ]
        md.append("| " + " | ".join(row) + " |")

    md.append("\n---\n")
    md.append("### 2. Análisis Detallado Caso a Caso (Expedientes de Comité)\n")

    for i, c in enumerate(casos, 1):
        md.append(f"#### Caso {i}: {c['archivo']} — {c['razon_social']} (`{c['rut']}`)")
        md.append(f"- **Régimen Tributario:** {c['regimen']}")
        md.append(f"- **Giro / Actividad Principal:** {c['actividad']}")
        md.append(f"- **Muestra Analizada:** {c['meses_f29']} declaraciones F29 | {c['num_f22']} formularios F22")
        md.append(f"- **Veredicto Final:** **{c['veredicto']}** | **Score:** {c['score']:.1f}/100 ({c['cat_riesgo']})")
        md.append(f"- **Desglose Scoring (3 Pilares):** Mora Efectiva: `{c['score_mora']}/100` | Margen Operacional: `{c['score_margen']}/100` | Respaldo CPT: `{c['score_respaldo']}/100`")
        md.append(f"- **Cupo Solicitado:** {fmt_pesos(c['cupo_solicitado'])}")
        md.append(f"- **Cupo Máximo Sugerido:** {fmt_pesos(c['cupo_maximo'])}")
        md.append(f"- **Cupo Aprobado:** **{fmt_pesos(c['cupo_aprobado'])}** (Plazo: {c['plazo_dias']} días)")
        md.append(f"- **Condiciones y Garantías:** {c['garantia'] or 'Sin garantías adicionales requeridas'}")
        md.append(f"\n> 📋 **Dictamen Ejecutivo de Comité:**\n> {c['dictamen']}\n")

        if c["meses_f29"] == 0 and c["num_f22"] == 0:
            md.append("\n> ℹ️ **Nota de Auditoría:** El archivo no corresponde a una Carpeta Tributaria oficial del SII (es un Balance o Estado Financiero independiente sin formularios F29 ni F22). El motor clasifica el expediente en estado OBSERVADO por falta de información fiscal.\n")

        mc = c["memoria_calculo"]
        if mc:
            md.append("##### 🧮 Memoria de Cálculo Cuantitativa (Algoritmo Pasos A-D)")
            md.append(f"- **Paso A (Base Compras Operacionales Mensuales C_base):** {fmt_pesos(mc.get('base_compras_c_base'))}")
            md.append(f"- **Paso B (Techo Operativo 20% Ventas Mensuales):** {fmt_pesos(mc.get('techo_operativo_20pct'))}")
            phi_val = mc.get('factor_riesgo_phi', 0.0)
            md.append(f"- **Paso C (Factor Calidad Crediticia Φ):** `{phi_val:.2f}` (Cupo Preliminar: {fmt_pesos(mc.get('cupo_preliminar'))})")
            cpt_tope = mc.get('tope_patrimonial_35pct_cpt')
            freno = cpt_tope is not None and mc.get('cupo_maximo_sugerido') == cpt_tope
            md.append(f"- **Paso D (Freno Patrimonial CPT):** {'⚠️ APLICADO (Tope 35% CPT: ' + fmt_pesos(cpt_tope) + ')' if freno else ('No limitó cupo (Suficiente respaldo CPT: ' + fmt_pesos(cpt_tope) + ')' if cpt_tope else 'Sin restricción por CPT')}")
            if mc.get("castigos_aplicados"):
                md.append(f"- **Castigos / Penalizaciones activas:** {', '.join(mc.get('castigos_aplicados'))}")
            md.append("")

        if c["banderas_rojas"]:
            md.append("##### 🚩 Banderas Rojas Detectadas")
            for b in c["banderas_rojas"]:
                md.append(f"- 🔴 {b}")
            md.append("")

        if c["hoja_ruta"]:
            md.append("##### 🧭 Hoja de Ruta Comercial y Mitigación")
            for h in c["hoja_ruta"]:
                md.append(f"- 💡 {h}")
            md.append("")

        md.append("---\n")

    output_path = Path("RESULTADOS_COMITE_V2.md")
    output_text = "\n".join(md)
    output_path.write_text(output_text, encoding="utf-8")
    print(f"\nReporte guardado exitosamente en: {output_path.resolve()}")


if __name__ == "__main__":
    main()
