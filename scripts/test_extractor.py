import json
from pathlib import Path

from src.extractors.pdf_extractor import PDFExtractor

PDF_PATH = Path("examples/carpeta_tributaria.pdf")
OUTPUT_PATH = Path("output/extract.json")
CHARS_PREVIEW = 500


def main() -> None:
    extractor = PDFExtractor()
    result = extractor.extract(PDF_PATH)

    num_pages = len(result.pages)
    total_chars = sum(len(p.text) for p in result.pages)
    first_page_preview = result.pages[0].text[:CHARS_PREVIEW] if result.pages else ""

    print(f"Páginas:          {num_pages}")
    print(f"Caracteres totales: {total_chars}")
    print(f"Primeras {CHARS_PREVIEW} letras (pág. 1):")
    print(first_page_preview)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        result.model_dump_json(indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nResultado guardado en {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
