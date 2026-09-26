import gc
import io
import json

from src.core.tax_folder_engine import TaxFolderEngine
from src.credit.anonymous_telemetry import registrar_telemetria_anonima
from src.reports.executive_report import ExecutiveReport


def process_pdf(uploaded_file, cupo_solicitado: int | None = None) -> tuple:
    """Procesa un PDF de Carpeta Tributaria 100% en memoria RAM (Zero-PII).

    El archivo jamás se escribe a disco. Tras la extracción, los buffers
    y descriptores volátiles se cierran y limpian con recolección de basura.
    """
    buffer = None
    try:
        pdf_bytes = uploaded_file.getvalue()
        buffer = io.BytesIO(pdf_bytes)

        engine = TaxFolderEngine(buffer)
        result = engine.parse(cupo_solicitado=cupo_solicitado)

        # Captura de telemetría estadística 100% anónima para calibración sectorial
        try:
            registrar_telemetria_anonima(result)
        except Exception:
            pass

        json_bytes = result.model_dump_json(
            indent=2, ensure_ascii=False
        ).encode("utf-8")

        report = ExecutiveReport()
        markdown = report.generate(result, result.kpis, result.analysis)
        markdown_bytes = markdown.encode("utf-8")

        return result, json_bytes, markdown_bytes

    finally:
        if buffer is not None:
            buffer.close()
        del buffer
        gc.collect()
