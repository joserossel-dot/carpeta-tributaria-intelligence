import json
import sys
from pathlib import Path

from src.core.tax_folder_engine import TaxFolderEngine


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: python scripts/parse_folder.py <ruta_al_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    if not Path(pdf_path).exists():
        print(f"Error: archivo no encontrado: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    engine = TaxFolderEngine(pdf_path)
    result = engine.parse()

    print(result.model_dump_json(indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
