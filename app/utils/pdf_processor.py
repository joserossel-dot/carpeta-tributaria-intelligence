import json
import tempfile
from pathlib import Path

from src.core.tax_folder_engine import TaxFolderEngine
from src.reports.executive_report import ExecutiveReport


def process_pdf(uploaded_file) -> tuple:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name

    try:
        engine = TaxFolderEngine(tmp_path)
        result = engine.parse()

        json_bytes = result.model_dump_json(
            indent=2, ensure_ascii=False
        ).encode("utf-8")

        report = ExecutiveReport()
        markdown = report.generate(result, result.kpis, result.analysis)
        markdown_bytes = markdown.encode("utf-8")

        return result, json_bytes, markdown_bytes
    finally:
        Path(tmp_path).unlink(missing_ok=True)
