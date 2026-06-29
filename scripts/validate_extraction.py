import signal
import sys
import time
from pathlib import Path

from src.core.tax_folder_engine import TaxFolderEngine

EXAMPLES_DIR = Path("examples")
REPORT_PATH = Path("output/reports/extraction_report.md")
FILE_TIMEOUT = 60


class TimeoutError(Exception):
    pass


def _handler(_signum, _frame) -> None:
    raise TimeoutError("timeout")


def process_pdf(pdf_path: Path) -> dict:
    signal.signal(signal.SIGALRM, _handler)
    signal.alarm(FILE_TIMEOUT)
    t0 = time.perf_counter()
    try:
        engine = TaxFolderEngine(str(pdf_path))
        result = engine.parse()
        elapsed = round(time.perf_counter() - t0, 2)
        total_codigos = sum(len(f.detalles) for f in result.f29)
        return {
            "archivo": pdf_path.name,
            "paginas": result.metadata.pages,
            "f29": len(result.f29),
            "codigos": total_codigos,
            "tiempo_seg": elapsed,
            "error": None,
        }
    except TimeoutError:
        elapsed = round(time.perf_counter() - t0, 2)
        return {
            "archivo": pdf_path.name,
            "paginas": 0,
            "f29": 0,
            "codigos": 0,
            "tiempo_seg": elapsed,
            "error": "timeout",
        }
    except Exception as e:
        elapsed = round(time.perf_counter() - t0, 2)
        return {
            "archivo": pdf_path.name,
            "paginas": 0,
            "f29": 0,
            "codigos": 0,
            "tiempo_seg": elapsed,
            "error": str(e),
        }
    finally:
        signal.alarm(0)


def main() -> None:
    pdf_files = sorted(EXAMPLES_DIR.glob("*.pdf"))
    results: list[dict] = []

    print(f"Procesando {len(pdf_files)} PDFs...\n")

    for pdf_path in pdf_files:
        info = process_pdf(pdf_path)
        results.append(info)

        status = f"  ERROR: {info['error']}" if info["error"] else ""
        print(
            f"  {info['archivo']:50s}"
            f"  págs {info['paginas']:3d}"
            f"  F29 {info['f29']:2d}"
            f"  códigos {info['codigos']:5d}"
            f"  {info['tiempo_seg']:6.2f}s"
            f"{status}"
        )

    ok = [r for r in results if not r["error"]]
    total_paginas = sum(r["paginas"] for r in ok)
    total_f29 = sum(r["f29"] for r in ok)
    total_codigos = sum(r["codigos"] for r in ok)
    total_tiempo = sum(r["tiempo_seg"] for r in ok)
    promedio = round(total_tiempo / len(ok), 2) if ok else 0

    print(f"\n  {'TOTAL':50s}  págs {total_paginas:3d}  F29 {total_f29:2d}  códigos {total_codigos:5d}  {total_tiempo:6.2f}s")

    md = (
        "# Reporte de Extracción - CarpetaTributaria\n\n"
        f"Generado: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "## Estadísticas Generales\n\n"
        f"| Métrica | Valor |\n"
        f"|---|---|\n"
        f"| PDFs procesados | {len(results)} |\n"
        f"| PDFs exitosos | {len(ok)} |\n"
        f"| PDFs con error | {len(results) - len(ok)} |\n"
        f"| Total páginas | {total_paginas} |\n"
        f"| Total F29 encontrados | {total_f29} |\n"
        f"| Total códigos tributarios extraídos | {total_codigos} |\n"
        f"| Tiempo total | {total_tiempo}s |\n"
        f"| Tiempo promedio por PDF | {promedio}s |\n\n"
        "## Detalle por Archivo\n\n"
        "| Archivo | Páginas | F29 | Códigos | Tiempo (s) | Error |\n"
        "|---|---|---|---|---|---|\n"
    )
    for r in sorted(results, key=lambda x: x["archivo"]):
        err = r["error"] or ""
        md += f"| {r['archivo']} | {r['paginas']} | {r['f29']} | {r['codigos']} | {r['tiempo_seg']} | {err} |\n"

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(md, encoding="utf-8")
    print(f"\nReporte guardado en {REPORT_PATH}")


if __name__ == "__main__":
    main()
