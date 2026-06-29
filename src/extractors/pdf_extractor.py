from pathlib import Path

import pdfplumber

from src.models.extract_result import ExtractResult, PageResult


class PDFExtractor:
    """Extractor de texto plano desde archivos PDF usando pdfplumber.

    No realiza interpretación ni parsing del contenido.
    Solo extrae el texto página por página.
    """

    def extract(self, pdf_path: str | Path) -> ExtractResult:
        """Extrae el texto de todas las páginas de un PDF.

        Args:
            pdf_path: Ruta al archivo PDF.

        Returns:
            ExtractResult con la lista de páginas y su texto.

        Raises:
            FileNotFoundError: Si el archivo no existe.
            pdfplumber.pdfminer.pdfparser.PDFSyntaxError: Si el PDF es inválido.
        """
        path = Path(pdf_path)

        if not path.exists():
            raise FileNotFoundError(f"PDF no encontrado: {path}")

        pages: list[PageResult] = []

        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append(PageResult(page=i, text=text))

        return ExtractResult(pages=pages)
