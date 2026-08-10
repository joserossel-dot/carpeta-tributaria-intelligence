"""Benchmark de ratio débito/crédito (proxy de margen) por código de
actividad económica del SII.

No existe una fuente pública que publique este ratio por rubro (se
investigó el Portal de Estadísticas Tributarias del SII -- publica
ventas y remuneraciones por rubro, no márgenes). Este store se construye
con el propio portafolio de carpetas procesadas: cada vez que se procesa
una carpeta con giro conocido, se registra su ratio aquí. El promedio de
un rubro solo se considera confiable con una muestra mínima.
"""

import json
from pathlib import Path

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
        if not codigo_actividad or codigo_actividad not in self._data:
            return None, 0
        entry = self._data[codigo_actividad]
        n = entry.get("n_empresas", 0)
        if n < MUESTRA_MINIMA_CONFIABLE:
            return None, n
        return entry.get("ratio_promedio"), n

    def registrar_muestra(self, codigo_actividad: str, ratio: float) -> None:
        """Agrega una observación al promedio móvil del rubro. Se llama
        una vez por carpeta procesada (no por período), para no sobre
        ponderar a una sola empresa con muchos meses de historia."""
        if not codigo_actividad or ratio is None:
            return
        entry = self._data.get(codigo_actividad, {"n_empresas": 0, "ratio_promedio": 0.0})
        n_anterior = entry["n_empresas"]
        promedio_anterior = entry["ratio_promedio"]
        n_nuevo = n_anterior + 1
        promedio_nuevo = (promedio_anterior * n_anterior + ratio) / n_nuevo
        self._data[codigo_actividad] = {
            "n_empresas": n_nuevo,
            "ratio_promedio": round(promedio_nuevo, 4),
        }
        self._save()
