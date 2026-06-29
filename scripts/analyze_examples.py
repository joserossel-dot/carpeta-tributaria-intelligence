import json
import signal
import time
from pathlib import Path

from src.extractors.pdf_extractor import PDFExtractor

EXAMPLES_DIR = Path("examples")
OUTPUT_PATH = Path("output/summary.json")
FILE_TIMEOUT = 30


class TimeoutError(Exception):
    pass


def _timeout_handler(_signum, _frame) -> None:
    raise TimeoutError("Tiempo de procesamiento excedido")


def extract_with_timeout(extractor: PDFExtractor, pdf_path: Path) -> dict:
    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(FILE_TIMEOUT)
    t0 = time.perf_counter()
    try:
        result = extractor.extract(pdf_path)
        elapsed = round(time.perf_counter() - t0, 4)
        info = {
            "archivo": pdf_path.name,
            "paginas": len(result.pages),
            "caracteres": sum(len(p.text) for p in result.pages),
            "tiempo_seg": elapsed,
            "error": None,
        }
    except Exception as e:
        elapsed = round(time.perf_counter() - t0, 4)
        info = {
            "archivo": pdf_path.name,
            "paginas": 0,
            "caracteres": 0,
            "tiempo_seg": elapsed,
            "error": str(e),
        }
    finally:
        signal.alarm(0)
    return info


def main() -> None:
    pdf_files = sorted(EXAMPLES_DIR.glob("*.pdf"))
    extractor = PDFExtractor()
    summary: list[dict] = []

    for pdf_path in pdf_files:
        info = extract_with_timeout(extractor, pdf_path)
        summary.append(info)

        status = f"  ERROR: {info['error']}" if info["error"] else ""
        print(
            f"{pdf_path.name:50s}  "
            f"{info['paginas']:3d} págs  "
            f"{info['caracteres']:7d} chars  "
            f"{info['tiempo_seg']:6.2f}s"
            f"{status}"
        )

    total_pages = sum(s["paginas"] for s in summary)
    total_chars = sum(s["caracteres"] for s in summary)
    total_time = round(sum(s["tiempo_seg"] for s in summary), 4)

    print(f"\n{'TOTAL':50s}  {total_pages:3d} págs  {total_chars:7d} chars  {total_time:6.2f}s")
    print(f"\nDocumentos analizados: {len(summary)}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Resumen guardado en {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
