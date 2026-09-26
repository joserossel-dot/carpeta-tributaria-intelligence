"""Benchmark de ratio débito/crédito (proxy de margen) por código de
actividad económica del SII.

No existe una fuente pública que publique este ratio por rubro (se
investigó el Portal de Estadísticas Tributarias del SII -- publica
ventas y remuneraciones por rubro, no márgenes). Este store se construye
con el propio portafolio de carpetas procesadas: cada vez que se procesa
una carpeta con giro conocido, se registra su ratio aquí. El promedio de
un rubro solo se considera confiable con una muestra mínima.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.credit.anonymous_telemetry import AnonymousBenchmarkRecord

MUESTRA_MINIMA_CONFIABLE = 15

_DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "sector_benchmarks.json"


class SectorBenchmark:
    def __init__(self, path: Path | None = None):
        self.path = path or _DEFAULT_PATH
        self._data: dict[str, dict] = self._load()

    def _load(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def lookup(self, codigo_actividad: str | None) -> tuple[float | None, int]:
        """Devuelve (ratio_promedio, n_empresas). ratio_promedio es None
        si no hay datos o la muestra es insuficiente para confiar en ella
        -- el caller decide qué hacer con n_empresas < MUESTRA_MINIMA."""
        if not codigo_actividad or str(codigo_actividad) not in self._data:
            return None, 0
        entry = self._data[str(codigo_actividad)]
        n = entry.get("n_empresas", 0)
        if n < MUESTRA_MINIMA_CONFIABLE:
            return None, n
        return entry.get("ratio_promedio"), n

    def get_sector_stats(
        self, codigo_actividad: str | None, include_private: bool = False
    ) -> dict | None:
        """Devuelve el registro estadístico completo para un código de actividad."""
        if not codigo_actividad or str(codigo_actividad) not in self._data:
            return None
        entry = dict(self._data[str(codigo_actividad)])
        if not include_private:
            entry.pop("fingerprints", None)
            entry.pop("_fingerprints", None)
        return entry

    def get_all(self, include_private: bool = False) -> dict[str, dict]:
        """Devuelve una copia de todos los benchmarks sectoriales.
        Por defecto oculta huellas internas (fingerprints) para proteger la privacidad."""
        if include_private:
            return dict(self._data)
        public_data = {}
        for k, v in self._data.items():
            entry = dict(v)
            entry.pop("fingerprints", None)
            entry.pop("_fingerprints", None)
            public_data[k] = entry
        return public_data

    def registrar_muestra(self, codigo_actividad: str, ratio: float) -> None:
        """Agrega una observación al promedio móvil del rubro. Se llama
        una vez por carpeta procesada (no por período), para no sobre
        ponderar a una sola empresa con muchos meses de historia."""
        if not codigo_actividad or ratio is None:
            return
        codigo = str(codigo_actividad)
        entry = self._data.get(
            codigo,
            {
                "n_empresas": 0,
                "ratio_promedio": 0.0,
                "margen_bruto_promedio": 0.0,
                "ratio_compras_ventas_promedio": 0.0,
                "distribucion_tramos": {},
                "_fingerprints": [],
            },
        )
        n_anterior = entry.get("n_empresas", 0)
        promedio_anterior = entry.get("ratio_promedio", 0.0)
        n_nuevo = n_anterior + 1
        promedio_nuevo = (promedio_anterior * n_anterior + ratio) / n_nuevo
        entry["n_empresas"] = n_nuevo
        entry["ratio_promedio"] = round(promedio_nuevo, 4)
        self._data[codigo] = entry
        self._save()

    def registrar_record(self, record: AnonymousBenchmarkRecord) -> bool:
        """Registra un AnonymousBenchmarkRecord actualizando promedios de forma deduplicada.

        Garantiza Zero-PII:
        - Verifica y agrega deduplicación por fingerprint de 16 caracteres.
        - Actualiza número de empresas observadas y promedios sectoriales.
        - Registra distribución por tramo de ventas.
        - Guarda las huellas en clave privada interna `_fingerprints`.
        """
        codigo = str(record.codigo_actividad)
        if not codigo:
            return False

        entry = self._data.get(
            codigo,
            {
                "n_empresas": 0,
                "ratio_promedio": 0.0,
                "margen_bruto_promedio": 0.0,
                "ratio_compras_ventas_promedio": 0.0,
                "distribucion_tramos": {},
                "_fingerprints": [],
            },
        )

        fingerprints: list[str] = entry.get("_fingerprints") or entry.get("fingerprints") or []
        if record.fingerprint in fingerprints:
            # Documento ya procesado previamente, no duplicar muestra
            return False

        n_ant = entry.get("n_empresas", 0)
        n_nuevo = n_ant + 1

        # Ratio debito/credito
        ratio_dc = record.ratio_debito_credito
        if ratio_dc is None and record.ratio_compras_ventas > 0:
            ratio_dc = round(1.0 / record.ratio_compras_ventas, 4)
        ratio_dc = ratio_dc or 1.0

        prom_dc_ant = entry.get("ratio_promedio", 0.0) or ratio_dc
        prom_dc_nuevo = (
            round((prom_dc_ant * n_ant + ratio_dc) / n_nuevo, 4) if n_ant > 0 else ratio_dc
        )

        # Margen bruto proxy
        margen_ant = entry.get("margen_bruto_promedio", 0.0)
        margen_nuevo = (
            round((margen_ant * n_ant + record.margen_bruto_proxy) / n_nuevo, 4)
            if n_ant > 0
            else record.margen_bruto_proxy
        )

        # Ratio compras / ventas
        cv_ant = entry.get("ratio_compras_ventas_promedio", 0.0)
        cv_nuevo = (
            round((cv_ant * n_ant + record.ratio_compras_ventas) / n_nuevo, 4)
            if n_ant > 0
            else record.ratio_compras_ventas
        )

        # Distribución de tramos
        tramos = entry.get("distribucion_tramos", {})
        tramos[record.tramo_ventas_anuales] = tramos.get(record.tramo_ventas_anuales, 0) + 1

        # Guardar deduplicación en clave interna privada
        fingerprints.append(record.fingerprint)
        if len(fingerprints) > 500:
            fingerprints = fingerprints[-500:]

        entry["n_empresas"] = n_nuevo
        entry["ratio_promedio"] = prom_dc_nuevo
        entry["margen_bruto_promedio"] = margen_nuevo
        entry["ratio_compras_ventas_promedio"] = cv_nuevo
        entry["distribucion_tramos"] = tramos
        entry["_fingerprints"] = fingerprints
        entry.pop("fingerprints", None)

        self._data[codigo] = entry
        self._save()
        return True

