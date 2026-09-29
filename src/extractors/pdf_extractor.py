import gc
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
        batch_size = 10

        if hasattr(pdf_source, "seek"):
            pdf_source.seek(0)

        with pdfplumber.open(pdf_source) as p_info:
            total_pages = len(p_info.pages)

        for start in range(1, total_pages + 1, batch_size):
            end = min(start + batch_size, total_pages + 1)
            page_nums = list(range(start, end))
            if hasattr(pdf_source, "seek"):
                pdf_source.seek(0)
            with pdfplumber.open(pdf_source, pages=page_nums) as pdf:
                for page in pdf.pages:
                    i = page.page_number
                    text = page.extract_text() or ""
                    if i <= 3 or "REPRESENTANTE" in text.upper() or "SOCIOS" in text.upper():
                        tables = page.extract_tables() or []
                    else:
                        tables = []

                    column_text = None
                    text_upper = text.upper()
                    if "FORMULARIO 22" in text_upper or "AÑO TRIBUTARIO" in text_upper or "FORM. 22" in text_upper:
                        try:
                            column_text = self._reconstruct_two_columns(page)
                        except Exception:
                            column_text = None

                    pages.append(PageResult(page=i, text=text, tables=tables, column_text=column_text))
                    page.flush_cache()
            gc.collect()

        return ExtractResult(pages=pages)

    @staticmethod
    def _reconstruct_two_columns(page) -> str:
        """Separa geométricamente las páginas de F22 en 2 columnas verticales (x0 < 400 y x0 >= 400)
        para evitar el intercalado horizontal de líneas de códigos paralelos.
        """
        words = page.extract_words()
        if not words:
            return ""
        split_x = 400.0 if page.width and page.width <= 650 else (page.width * 0.50 if page.width else 400.0)
        left_words = [w for w in words if w["x0"] < split_x]
        right_words = [w for w in words if w["x0"] >= split_x]

        def words_to_lines(wlist):
            if not wlist:
                return ""
            wlist = sorted(wlist, key=lambda w: (round(w["top"], 1), w["x0"]))
            lines = []
            cur_line = []
            cur_top = None
            for w in wlist:
                if cur_top is None or abs(w["top"] - cur_top) > 3.0:
                    if cur_line:
                        lines.append(" ".join(cur_line))
                    cur_line = [w["text"]]
                    cur_top = w["top"]
                else:
                    cur_line.append(w["text"])
            if cur_line:
                lines.append(" ".join(cur_line))
            return "\n".join(lines)

        left_text = words_to_lines(left_words)
        right_text = words_to_lines(right_words)
        return left_text + "\n" + right_text

