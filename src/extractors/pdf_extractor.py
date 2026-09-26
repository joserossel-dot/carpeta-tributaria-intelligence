import io
from pathlib import Path
from typing import BinaryIO

import pdfplumber

from src.models.extract_result import ExtractResult, PageResult


class PDFExtractor:
    """Extractor de texto plano desde archivos PDF usando pdfplumber.

    No realiza interpretación ni parsing del contenido.
    Solo extrae el texto página por página. Soporta archivos en disco
    o flujos binarios 100% en memoria (Zero-PII).
    """

    def extract(self, pdf_input: str | Path | bytes | BinaryIO) -> ExtractResult:
        """Extrae el texto de todas las páginas de un PDF.

        Args:
            pdf_input: Ruta al archivo PDF o stream en memoria (BytesIO/bytes).

        Returns:
            ExtractResult con la lista de páginas y su texto.

        Raises:
            FileNotFoundError: Si el archivo no existe.
            pdfplumber.pdfminer.pdfparser.PDFSyntaxError: Si el PDF es inválido.
        """
        if isinstance(pdf_input, (str, Path)):
            path = Path(pdf_input)
            if not path.exists():
                raise FileNotFoundError(f"PDF no encontrado: {path}")
            pdf_source = path
        elif isinstance(pdf_input, bytes):
            pdf_source = io.BytesIO(pdf_input)
        else:
            pdf_source = pdf_input

        pages: list[PageResult] = []

        with pdfplumber.open(pdf_source) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append(PageResult(page=i, text=text))

        return ExtractResult(pages=pages)

