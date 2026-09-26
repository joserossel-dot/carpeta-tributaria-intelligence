#!/usr/bin/env python3
"""Script para poblar data/sector_benchmarks.json con telemetría estadística anónima
a partir de las carpetas tributarias de ejemplo, verificando Zero-PII Retention.
"""

import gc
import io
import json
from pathlib import Path

from src.core.tax_folder_engine import TaxFolderEngine
from src.credit.anonymous_telemetry import extraer_registro_anonimo
from src.credit.sector_benchmark import SectorBenchmark

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
BENCHMARK_PATH = Path(__file__).resolve().parents[1] / "data" / "sector_benchmarks.json"


def main():
    print("=== SEEDING SECTOR BENCHMARKS (Zero-PII) ===")
    bench = SectorBenchmark(BENCHMARK_PATH)
    known_pii = []

    pdf_files = [
        "CPTAgrGonzagriLtda.pdf",
        "CPTAgrGonzalezLtda.pdf",
        "CPTExportadora.pdf",
        "CPTGonzagriS.A..pdf",
        "Carpeta Tributaria.CLINICA HYPERBARIC.pdf",
        "Carpeta_Tributaria_Regular (4).pdf",
        "carpeta_tributaria.pdf",
    ]

    registrados = 0
    for pdf_name in pdf_files:
        pdf_path = EXAMPLES_DIR / pdf_name
        if not pdf_path.exists():
            continue

        raw_bytes = pdf_path.read_bytes()
        buf = io.BytesIO(raw_bytes)

        try:
            engine = TaxFolderEngine(buf)
            tax_folder = engine.parse()

            # Guardar PII para verificación estricta posterior
            if tax_folder.contributor:
                if tax_folder.contributor.rut:
                    rut = tax_folder.contributor.rut.replace(".", "").replace("-", "").strip()
                    if rut:
                        known_pii.append(rut)
                if tax_folder.contributor.razon_social:
                    rs = tax_folder.contributor.razon_social.strip()
                    if len(rs) > 4:
                        known_pii.append(rs)

            record = extraer_registro_anonimo(tax_folder)
            if record:
                added = bench.registrar_record(record)
                if added:
                    registrados += 1
                    print(f" [+] Registrado rubro {record.codigo_actividad} | tramo: {record.tramo_ventas_anuales} | fp: {record.fingerprint}")
                else:
                    print(f" [=] Ya existía fingerprint {record.fingerprint}")
            else:
                print(f" [-] Sin ventas o actividad para {pdf_name}")
        finally:
            buf.close()
            del buf
            del raw_bytes
            gc.collect()

    print(f"\nTotal registros nuevos agregados: {registrados}")

    # Verificación Forense Zero-PII en el archivo persistido
    content = BENCHMARK_PATH.read_text(encoding="utf-8")
    for pii in known_pii:
        if pii.lower() in content.lower():
            raise AssertionError(f"ALERTA CRÍTICA: PII encontrada en sector_benchmarks.json: {pii}")

    print(" [✓] Verificación Zero-PII exitosa: ningún RUT ni Razón Social está presente en data/sector_benchmarks.json")
    print("\nDataset actual de benchmarks:")
    print(content)


if __name__ == "__main__":
    main()
