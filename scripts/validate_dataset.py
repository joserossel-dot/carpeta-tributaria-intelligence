import time as time_mod
from collections import Counter
from pathlib import Path

from src.core.tax_folder_engine import TaxFolderEngine


def _check_field(result, *keys):
    try:
        val = result
        for k in keys:
            val = getattr(val, k, None)
            if val is None:
                return True
        if isinstance(val, (list, str)) and len(val) == 0:
            return True
        return False
    except Exception:
        return True


def _gather_field_groups(result):
    c = result.contributor
    k = result.kpis
    return {
        "RUT": _check_field(c, "rut"),
        "Razón Social": _check_field(c, "razon_social"),
        "Fecha Generación": _check_field(c, "fecha_generacion"),
        "Inicio Actividades": _check_field(c, "fecha_inicio_actividades"),
        "Domicilio": _check_field(c, "domicilio"),
        "Comuna": _check_field(c, "comuna"),
        "Región": _check_field(c, "region"),
        "Tipo Contribuyente": _check_field(c, "tipo_contribuyente"),
        "Régimen Tributario": _check_field(c, "regimen_tributario"),
        "Actividades Económicas": len(result.activities) == 0,
        "Actividad Principal": _check_field(k, "principal_activity"),
        "Antigüedad": _check_field(k, "company_age_years"),
        "Declaraciones F29": len(result.f29) == 0,
        "Representantes": len(result.representatives) == 0,
        "Propiedades": len(result.properties) == 0,
        "Vehículos": len(result.vehicles) == 0,
    }


def main() -> None:
    examples = sorted(Path("examples").glob("*.pdf"))
    rows: list[dict] = []
    all_missing: Counter = Counter()
    total = len(examples)

    print(f"Procesando {total} archivos...\n")

    for pdf in examples:
        t0 = time_mod.perf_counter()
        error = None
        result = None
        try:
            engine = TaxFolderEngine(str(pdf))
            result = engine.parse()
            elapsed = time_mod.perf_counter() - t0
        except Exception as e:
            elapsed = time_mod.perf_counter() - t0
            error = str(e)

        entry = {
            "archivo": pdf.name,
            "exito": error is None,
            "error": error,
            "paginas": result.metadata.pages if result else 0,
            "tiempo": round(elapsed, 3),
            "empresa": result.contributor.razon_social if result and result.contributor else None,
            "rut": result.contributor.rut if result and result.contributor else None,
            "regimen": result.contributor.regimen_tributario if result and result.contributor else None,
            "actividades": len(result.activities) if result else 0,
            "f29": len(result.f29) if result else 0,
            "representantes": len(result.representatives) if result else 0,
        }
        rows.append(entry)

        if result:
            missing = _gather_field_groups(result)
            for field, is_missing in missing.items():
                if is_missing:
                    all_missing[field] += 1

        status = "OK" if error is None else "ERROR"
        print(f"  [{status:5s}] {pdf.name}  ({entry['tiempo']}s)")

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    successes = [r for r in rows if r["exito"]]
    errors = [r for r in rows if not r["exito"]]
    times = [r["tiempo"] for r in rows if r["exito"]]
    avg_time = sum(times) / len(times) if times else 0.0
    max_time = max(times) if times else 0.0

    sorted_missing = all_missing.most_common()
    total_ok = len(successes)

    lines: list[str] = []
    lines.append("# Informe de Validación — Dataset de Carpetas Tributarias\n")
    lines.append(f"**Fecha:** {time_mod.strftime('%Y-%m-%d %H:%M')}\n")
    lines.append(f"**Total archivos:** {total}\n")

    lines.append("## Resumen General\n")
    lines.append(f"- **Exitosos:** {total_ok}")
    lines.append(f"- **Con errores:** {len(errors)}")
    lines.append(f"- **Tiempo promedio:** {avg_time:.2f}s")
    lines.append(f"- **Tiempo máximo:** {max_time:.2f}s")
    lines.append("")

    lines.append("## Detalle por Archivo\n")
    lines.append("| Archivo | Estado | Págs | Tiempo | Empresa | RUT | Régimen | Act. | F29 | Rep. |")
    lines.append("|---------|--------|------|--------|---------|-----|---------|------|-----|------|")

    for r in rows:
        estado = "✅ OK" if r["exito"] else "❌ ERROR"
        emp = (r["empresa"] or "—")[:30]
        rut_val = r["rut"] or "—"
        reg = (r["regimen"] or "—")[:25]
        lines.append(
            f"| {r['archivo'][:40]:40s} | {estado:7s} | {r['paginas']:>4d} | "
            f"{r['tiempo']:>6.2f}s | {emp:30s} | {rut_val:12s} | {reg:25s} | "
            f"{r['actividades']:>3d} | {r['f29']:>3d} | {r['representantes']:>3d} |"
        )

    if errors:
        lines.append("\n## Archivos con Errores\n")
        for r in errors:
            lines.append(f"- **{r['archivo']}:** {r['error']}")

    lines.append("\n## Campos con Mayor Porcentaje de Valores Faltantes\n")
    lines.append("| Campo | Faltantes | Porcentaje |")
    lines.append("|-------|-----------|------------|")
    for field, count in sorted_missing:
        pct = round(count / total_ok * 100, 1) if total_ok else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        lines.append(f"| {field:30s} | {count:>3d}/{total_ok:<3d} | {pct:>5.1f}% {bar} |")

    lines.append("")

    report_path = output_dir / "validation_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReporte generado: {report_path.resolve()}")
    print(f"  {total_ok} exitosos, {len(errors)} fallidos")
    print(f"  tiempo promedio: {avg_time:.2f}s, máximo: {max_time:.2f}s")


if __name__ == "__main__":
    main()
