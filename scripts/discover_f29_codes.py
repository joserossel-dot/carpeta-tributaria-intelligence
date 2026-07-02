import json
from collections import defaultdict
from pathlib import Path

from src.core.tax_folder_engine import TaxFolderEngine

EXAMPLES = sorted(Path("examples").glob("*.pdf"))
OUTPUT_DIR = Path("output")


def _infer_category(codigo: str, glosa: str) -> str:
    c = codigo
    g = glosa.upper()
    if c in ("502", "503", "538", "512", "513", "509", "586", "714"):
        return "VENTAS"
    if c in ("520", "519", "511", "524", "525", "527", "528", "531", "532", "562", "584", "504", "077", "537"):
        return "COMPRAS"
    if c == "089":
        return "IVA"
    if c in ("062", "115"):
        return "PPM"
    if c == "563":
        return "BASE_IMPONIBLE"
    if c in ("048", "151"):
        return "RETENCIONES"
    if c in ("595", "547"):
        return "TOTALES"
    return "OTROS"


def main() -> None:
    codes: dict[str, dict] = {}

    for pdf in EXAMPLES:
        try:
            engine = TaxFolderEngine(str(pdf))
            result = engine.parse()
        except Exception:
            continue

        for f29 in result.f29:
            periodo = f29.periodo
            for det in f29.detalles:
                c = det.codigo
                try:
                    valor_num = int(det.valor.replace(".", "").replace(",", "."))
                except (ValueError, AttributeError):
                    valor_num = None

                if c not in codes:
                    codes[c] = {
                        "codigo": c,
                        "glosas": set(),
                        "conteo": 0,
                        "periodos": set(),
                        "valores": [],
                        "categoria": _infer_category(c, det.glosa),
                    }

                codes[c]["conteo"] += 1
                codes[c]["glosas"].add(det.glosa)
                codes[c]["periodos"].add(periodo)
                if valor_num is not None:
                    codes[c]["valores"].append(valor_num)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sorted_codes = sorted(codes.values(), key=lambda x: x["conteo"], reverse=True)

    for entry in sorted_codes:
        entry["glosas"] = sorted(entry["glosas"])
        entry["periodos"] = sorted(entry["periodos"])
        vals = entry.pop("valores")
        if vals:
            entry["valor_min"] = min(vals)
            entry["valor_max"] = max(vals)
            entry["muestra"] = sorted(set(vals))[:5]
        else:
            entry["valor_min"] = None
            entry["valor_max"] = None
            entry["muestra"] = []

    json_path = OUTPUT_DIR / "f29_codes.json"
    json_path.write_text(
        json.dumps(sorted_codes, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"JSON: {json_path.resolve()}")

    md_lines = [
        "# Catálogo de Códigos F29\n",
        f"**Total de códigos únicos:** {len(sorted_codes)}\n",
        "| Código | Categoría | Veces | Períodos | Valor Mín | Valor Máx | Muestra | Glosas |",
        "|--------|-----------|-------|----------|-----------|-----------|---------|--------|",
    ]

    for entry in sorted_codes:
        muestra = ", ".join(str(v) for v in entry["muestra"])
        if len(entry["muestra"]) < len(set(entry.get("valor_min") is not None and [1] or [])):
            muestra += "…"
        glosas_br = "<br>".join(entry["glosas"][:3])
        if len(entry["glosas"]) > 3:
            glosas_br += "<br>…"
        md_lines.append(
            f"| {entry['codigo']:>4s} | {entry['categoria']:15s} | {entry['conteo']:>5d} | "
            f"{entry['periodos'][0]}–{entry['periodos'][-1]} | "
            f"{_fmt(entry['valor_min']):>12s} | {_fmt(entry['valor_max']):>12s} | "
            f"{muestra:30s} | {glosas_br} |"
        )

    md_lines.append("")
    md_lines.append("## Categorías detectadas\n")
    cats = defaultdict(int)
    for e in sorted_codes:
        cats[e["categoria"]] += e["conteo"]
    for cat, total in sorted(cats.items(), key=lambda x: -x[1]):
        md_lines.append(f"- **{cat}:** {total} ocurrencias")

    md_path = OUTPUT_DIR / "f29_code_catalog.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"MD:  {md_path.resolve()}")
    print(f"\nCódigos únicos: {len(sorted_codes)}")


def _fmt(v: int | None) -> str:
    if v is None:
        return "—"
    return f"${v:>10,}"


if __name__ == "__main__":
    main()
