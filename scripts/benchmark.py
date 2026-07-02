import signal
import time
from pathlib import Path

from src.core.tax_folder_engine import TaxFolderEngine

EXAMPLES = sorted(Path("examples").glob("*.pdf"))
TIMEOUT = 120
PADDING = 55


class TimeoutError(Exception):
    pass


def _handler(_signum, _frame) -> None:
    raise TimeoutError()


signal.signal(signal.SIGALRM, _handler)


def bench_single(pdf_path: Path) -> dict:
    signal.alarm(TIMEOUT)
    t0 = time.perf_counter()
    try:
        engine = TaxFolderEngine(str(pdf_path))
        result = engine.parse()
        elapsed = time.perf_counter() - t0
        return {
            "archivo": pdf_path.name,
            "paginas": result.metadata.pages,
            "f29": len(result.f29),
            "codigos": sum(len(f.detalles) for f in result.f29),
            "tiempo": round(elapsed, 3),
            "error": None,
        }
    except TimeoutError:
        return {"archivo": pdf_path.name, "tiempo": TIMEOUT, "error": "timeout"}
    except Exception as e:
        return {"archivo": pdf_path.name, "tiempo": round(time.perf_counter() - t0, 3), "error": str(e)}
    finally:
        signal.alarm(0)


def main() -> None:
    ok = 0
    fail = 0
    total_pags = 0
    total_f29 = 0
    total_cods = 0
    total_time = 0.0

    print(f"\n  {'Archivo':{PADDING}}  {'Págs':>5}  {'F29':>4}  {'Códigos':>8}  {'Tiempo':>8}")
    print("  " + "-" * (PADDING + 5 + 4 + 8 + 8 + 4))

    for pdf in EXAMPLES:
        r = bench_single(pdf)
        if r.get("error"):
            print(f"  {r['archivo']:{PADDING}}  {'—':>5}  {'—':>4}  {'—':>8}  {r['tiempo']:>7.1f}s  ERROR: {r['error']}")
            fail += 1
        else:
            print(f"  {r['archivo']:{PADDING}}  {r['paginas']:>5}  {r['f29']:>4}  {r['codigos']:>8}  {r['tiempo']:>7.2f}s")
            ok += 1
            total_pags += r["paginas"]
            total_f29 += r["f29"]
            total_cods += r["codigos"]
            total_time += r["tiempo"]

    n = ok or 1
    print("  " + "-" * (PADDING + 5 + 4 + 8 + 8 + 4))
    print(f"  {'TOTAL (exitosos)':{PADDING}}  {total_pags:>5}  {total_f29:>4}  {total_cods:>8}  {total_time:>7.2f}s")
    print(f"\n  {ok} exitosos, {fail} fallidos — {total_time:.1f}s total, {total_time / n:.2f}s promedio")
    print()


if __name__ == "__main__":
    main()
