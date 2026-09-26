import gc
import io
import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.tax_folder_engine import TaxFolderEngine
from src.credit.anonymous_telemetry import (
    AnonymousBenchmarkRecord,
    clasificar_tramo_ventas,
    enviar_webhook_telemetria,
    extraer_registro_anonimo,
    generar_fingerprint,
    registrar_telemetria_anonima,
)
from src.credit.sector_benchmark import SectorBenchmark
from src.extractors.pdf_extractor import PDFExtractor
from src.models.activity import Activity
from src.models.contributor import Contributor
from src.models.credit_risk import (
    CreditRiskResult,
    Indicadores,
    MargenVsGiro,
    RespaldoEstructural,
)
from src.models.monthly_tax import MonthlyTax
from src.models.tax_folder import Metadata, TaxFolder
from src.services.monthly_tax_service import MonthlyTaxResult


def _create_mock_tax_folder(
    rut="76.999.888-K",
    razon_social="DISTRIBUIDORA CONFIDENCIAL CHILE SPA",
    codigo_giro="461001",
    ventas_12m=600_000_000,
    compras_12m=450_000_000,
) -> TaxFolder:
    contributor = Contributor(
        rut=rut,
        razon_social=razon_social,
    )
    activities = [
        Activity(codigo=codigo_giro, descripcion="VENTA AL POR MAYOR", principal=True)
    ]
    monthly_taxes = [
        MonthlyTax(
            periodo=f"2024-{m:02d}",
            total_ventas=Decimal(str(ventas_12m // 12)),
            compras=Decimal(str(compras_12m // 12)),
            debito_fiscal=Decimal("1000"),
            credito_fiscal=Decimal("800"),
        )
        for m in range(1, 13)
    ]
    monthly_analysis = MonthlyTaxResult(
        monthly_taxes=monthly_taxes,
        total_months=12,
        ventas_ultimos_12=Decimal(str(ventas_12m)),
        compras_ultimos_12=Decimal(str(compras_12m)),
        variacion_ventas_yoy_3m_pct=Decimal("12.5"),
    )
    credit_risk = CreditRiskResult(
        indicadores=Indicadores(
            margen_vs_giro=MargenVsGiro(ratio_debito_credito_12m=1.25),
            respaldo_estructural=RespaldoEstructural(capital_propio_tributario=150_000_000),
        ),
        cupo_aprobado=50_000_000,
    )

    return TaxFolder(
        metadata=Metadata(source_file="memory://test.pdf", pages=1, processing_time=0.1),
        contributor=contributor,
        activities=activities,
        monthly_taxes=monthly_taxes,
        monthly_analysis=monthly_analysis,
        credit_risk=credit_risk,
    )


class TestAnonymousBenchmarkRecord:
    def test_zero_pii_leakage(self):
        """Verifica rigurosamente que NINGÚN identificador (RUT, nombre)
        esté presente en el modelo o en su serialización JSON.
        """
        tf = _create_mock_tax_folder()
        record = extraer_registro_anonimo(tf)

        assert record is not None
        record_json = record.model_dump_json()

        # Comprobación de PII
        assert "76.999.888-K" not in record_json
        assert "76999888" not in record_json
        assert "CONFIDENCIAL" not in record_json
        assert "DISTRIBUIDORA" not in record_json
        assert "SPA" not in record_json

        # Comprobación de atributos
        forbidden_attrs = ["rut", "razon_social", "nombre", "socio", "representante", "domicilio"]
        for attr in forbidden_attrs:
            assert not hasattr(record, attr)

        # Campos numéricos normalizados
        assert record.codigo_actividad == "461001"
        assert record.tramo_ventas_anuales == "500M - 2.000M"
        assert record.ratio_compras_ventas == 0.75
        assert record.margen_bruto_proxy == 0.25
        assert record.ratio_debito_credito == 1.25
        assert record.ratio_cpt_ventas == round(150_000_000 / 600_000_000, 4)
        assert record.ratio_cupo_recomendado_ventas == round(50_000_000 / 600_000_000, 4)
        assert len(record.fingerprint) == 16

    def test_clasificar_tramo_ventas(self):
        assert clasificar_tramo_ventas(50_000_000) == "< 100M"
        assert clasificar_tramo_ventas(150_000_000) == "100M - 500M"
        assert clasificar_tramo_ventas(800_000_000) == "500M - 2.000M"
        assert clasificar_tramo_ventas(5_000_000_000) == "2.000M - 10.000M"
        assert clasificar_tramo_ventas(15_000_000_000) == "> 10.000M"

    def test_fingerprint_deterministic_and_unique(self):
        fp1 = generar_fingerprint("012400", "2024-05", 200_000_000, 150_000_000)
        fp2 = generar_fingerprint("012400", "2024-05", 200_000_000, 150_000_000)
        fp3 = generar_fingerprint("012400", "2024-06", 200_000_000, 150_000_000)

        assert fp1 == fp2
        assert fp1 != fp3
        assert len(fp1) == 16


class TestSectorBenchmarkIntegration:
    def test_registrar_record_deduplication(self, tmp_path):
        bench_file = tmp_path / "benchmarks_test.json"
        bench = SectorBenchmark(bench_file)

        tf = _create_mock_tax_folder(codigo_giro="681012")
        rec = extraer_registro_anonimo(tf)

        # Primer registro exitoso
        added_first = bench.registrar_record(rec)
        assert added_first is True

        # El resumen público NO debe exponer las huellas de deduplicación
        stats_public = bench.get_sector_stats("681012")
        assert stats_public["n_empresas"] == 1
        assert "fingerprints" not in stats_public
        assert "_fingerprints" not in stats_public

        # El dataset interno sí contiene la deduplicación
        stats_private = bench.get_sector_stats("681012", include_private=True)
        assert stats_private["_fingerprints"] == [rec.fingerprint]

        # Segundo registro con el mismo fingerprint se ignora (no altera promedios)
        added_second = bench.registrar_record(rec)
        assert added_second is False

        stats_after = bench.get_sector_stats("681012")
        assert stats_after["n_empresas"] == 1

        # Lookup funcional
        ratio, n = bench.lookup("681012")
        assert n == 1
        # Con 1 empresa < 15, ratio debe ser None para score
        assert ratio is None

    def test_exportadora_ratio_operacional_no_distorsionado(self):
        """Verifica que empresas con exportaciones > 20% usen el ratio
        operacional Ventas / Costo Operativo y no el Débito Fiscal IVA.
        """
        tf = _create_mock_tax_folder(
            codigo_giro="461001",
            ventas_12m=1_000_000_000,
            compras_12m=500_000_000,
        )
        # Asignar 80% de ventas a exportaciones en los 12 meses
        for mt in tf.monthly_taxes:
            mt.ventas_exportacion = mt.total_ventas * Decimal("0.80")
            mt.debito_fiscal = Decimal("200") # Débito ínfimo porque exportaciones no generan debito

        rec = extraer_registro_anonimo(tf)
        assert rec is not None
        # En vez del ratio tributario distorsionado, debe reflejar el ratio operacional
        assert rec.ratio_debito_credito == round(1_000_000_000 / 500_000_000, 4)
        assert rec.ratio_debito_credito == 2.0

    def test_giro_exento_aplica_piso_costo_proxy(self):
        """Verifica que empresas sin compras (servicios/rentistas)
        apliquen el piso de costo operativo del 30% de ventas y no 0% compras.
        """
        tf = _create_mock_tax_folder(
            codigo_giro="862021",
            ventas_12m=100_000_000,
            compras_12m=0, # Cero compras con IVA
        )
        for mt in tf.monthly_taxes:
            mt.compras = Decimal("0")
            mt.compras_operacionales = Decimal("0")

        rec = extraer_registro_anonimo(tf)
        assert rec is not None
        # Costo operativo mínimo = 30% de ventas (30M)
        assert rec.ratio_compras_ventas == 0.30
        assert rec.margen_bruto_proxy == 0.70

    def test_backward_compatibility_registrar_muestra(self, tmp_path):
        bench_file = tmp_path / "benchmarks_compat.json"
        bench = SectorBenchmark(bench_file)

        for _ in range(15):
            bench.registrar_muestra("999999", 2.5)

        ratio, n = bench.lookup("999999")
        assert n == 15
        assert ratio == 2.5


class TestInMemoryRAMProcessing:
    def test_tax_folder_engine_accepts_bytes_io(self):
        """Verifica que TaxFolderEngine acepta io.BytesIO sin escribir en disco."""
        sample_path = Path("examples/CPTAgrGonzagriLtda.pdf")
        if not sample_path.exists():
            pytest.skip("PDF de ejemplo no disponible")

        pdf_bytes = sample_path.read_bytes()
        buf = io.BytesIO(pdf_bytes)

        engine = TaxFolderEngine(buf)
        tax_folder = engine.parse()

        assert tax_folder.metadata.source_file == "memory://in-memory.pdf"
        assert tax_folder.contributor is not None
        assert len(tax_folder.f29) > 0

        buf.close()
        del buf
        del pdf_bytes
        gc.collect()


class TestWebhookDispatch:
    def test_webhook_disabled_by_default(self):
        tf = _create_mock_tax_folder()
        rec = extraer_registro_anonimo(tf)
        assert enviar_webhook_telemetria(rec) is False

    @patch("urllib.request.urlopen")
    def test_webhook_dispatches_when_env_set(self, mock_urlopen, monkeypatch):
        monkeypatch.setenv("TELEMETRY_WEBHOOK_URL", "https://telemetry.example.com/api/v1/records")
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        tf = _create_mock_tax_folder()
        rec = extraer_registro_anonimo(tf)
        success = enviar_webhook_telemetria(rec)

        assert success is True
        assert mock_urlopen.called
