import sys
from pathlib import Path

from src.core.tax_folder_engine import TaxFolderEngine
from src.reports.executive_report import ExecutiveReport


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: python scripts/generate_report.py <pdf_path>", file=sys.stderr)
        sys.exit(1)

    pdf_path = sys.argv[1]

    if not Path(pdf_path).exists():
        print(f"Error: archivo no encontrado: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    engine = TaxFolderEngine(pdf_path)
    result = engine.parse()

    report = ExecutiveReport()
    markdown = report.generate(result, result.kpis, result.analysis)

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "report.md"
    output_path.write_text(markdown, encoding="utf-8")

    print(f"Reporte generado: {output_path.resolve()}")


if __name__ == "__main__":
    main()
