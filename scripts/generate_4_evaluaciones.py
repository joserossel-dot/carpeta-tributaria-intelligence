"""Script para regenerar los 4 informes oficiales de Evaluación Tributaria en /Users/josealfonsorossel/Downloads/."""
import sys
from pathlib import Path

from src.core.tax_folder_engine import TaxFolderEngine
from src.reports.pdf_report import PDFReport

CASES = [
    {
        "rut": "762939398",
        "name": "ALVAL SPA",
        "input": Path("/Users/josealfonsorossel/Downloads/Carpeta_Tributaria_Regular (8).pdf"),
        "output": Path("/Users/josealfonsorossel/Downloads/evaluacion_tributaria_762939398.pdf"),
    },
    {
        "rut": "952140000",
        "name": "NUTRISA",
        "input": Path("/Users/josealfonsorossel/Downloads/Carpeta Tributaria Personalizada NUTRISA.pdf"),
        "output": Path("/Users/josealfonsorossel/Downloads/evaluacion_tributaria_952140000.pdf"),
    },
    {
        "rut": "781555401",
        "name": "PROTERM S.A.",
        "input": Path("/Users/josealfonsorossel/Downloads/Carpeta_Tributaria_Regular (4).pdf"),
        "output": Path("/Users/josealfonsorossel/Downloads/evaluacion_tributaria_781555401.pdf"),
    },
    {
        "rut": "774603859",
        "name": "CLINICA HYPERBARIC SPA",
        "input": (
            Path("/Users/josealfonsorossel/Downloads/Carpeta Tributaria.CLINICA HYPERBARIC.pdf")
            if Path("/Users/josealfonsorossel/Downloads/Carpeta Tributaria.CLINICA HYPERBARIC.pdf").exists()
            else Path("examples/Carpeta Tributaria.CLINICA HYPERBARIC.pdf")
        ),
        "output": Path("/Users/josealfonsorossel/Downloads/evaluacion_tributaria_774603859.pdf"),
    },
]


def main() -> None:
    report_gen = PDFReport()
    for case in CASES:
        print(f"Procesando {case['name']} ({case['rut']}) desde {case['input']}...")
        if not case["input"].exists():
            print(f"ADVERTENCIA: Archivo de entrada no existe: {case['input']}", file=sys.stderr)
            continue
        folder = TaxFolderEngine(str(case["input"])).parse()
        pdf_bytes = report_gen.generate(folder)
        case["output"].write_bytes(pdf_bytes)
        print(f"OK -> Generado {case['output']} ({len(pdf_bytes):,} bytes)")


if __name__ == "__main__":
    main()
