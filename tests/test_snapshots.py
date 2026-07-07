import json
from pathlib import Path

from src.core.tax_folder_engine import TaxFolderEngine

FIXTURES = sorted(Path("tests/fixtures").iterdir())


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TestSnapshot:
    def _get_fixtures(self) -> list[Path]:
        return [f for f in FIXTURES if f.is_dir() and (f / "input.pdf").exists()]

    def test_all_fixtures_match(self) -> None:
        errors: list[str] = []
        for fixture in self._get_fixtures():
            error = self._check_fixture(fixture)
            if error:
                errors.append(error)

        if errors:
            msg = "\n\n".join(errors)
            raise AssertionError(f"Snapshot mismatches:\n\n{msg}")

    def _check_fixture(self, fixture: Path) -> str | None:
        pdf_path = str(fixture / "input.pdf")
        expected = _load_json(fixture / "expected.json")
        engine = TaxFolderEngine(pdf_path)
        result = engine.parse()
        actual = result.model_dump(mode="json")

        actual["metadata"]["processing_time"] = 0.0
        # source_file es una ruta absoluta -- varia segun la maquina/usuario
        # que corre el test, no es parte del contrato de datos a validar.
        actual["metadata"]["source_file"] = ""
        expected["metadata"]["source_file"] = ""
        if actual.get("kpis"):
            actual["kpis"]["processing_timestamp"] = ""

        differences = self._deep_diff(expected, actual, path="")

        if not differences:
            return None

        lines = [
            f"=== {fixture.name} ===",
            *differences,
        ]
        return "\n".join(lines)

    @staticmethod
    def _deep_diff(a: dict, b: dict, path: str) -> list[str]:
        diffs: list[str] = []
        all_keys = set(a.keys()) | set(b.keys())
        for key in sorted(all_keys):
            p = f"{path}.{key}" if path else key
            if key not in a:
                diffs.append(f"  + {p}: key added (value={repr(b[key])[:200]})")
            elif key not in b:
                diffs.append(f"  - {p}: key removed (was={repr(a[key])[:200]})")
            elif isinstance(a[key], dict) and isinstance(b[key], dict):
                diffs.extend(TestSnapshot._deep_diff(a[key], b[key], p))
            elif isinstance(a[key], list) and isinstance(b[key], list):
                sub = TestSnapshot._list_diff(a[key], b[key], p)
                diffs.extend(sub)
            elif a[key] != b[key]:
                diffs.append(
                    f"  ~ {p}: {repr(a[key])[:120]} != {repr(b[key])[:120]}"
                )
        return diffs

    @staticmethod
    def _list_diff(a: list, b: list, path: str) -> list[str]:
        diffs: list[str] = []
        for i in range(max(len(a), len(b))):
            p = f"{path}[{i}]"
            if i >= len(a):
                diffs.append(f"  + {p}: item added")
            elif i >= len(b):
                diffs.append(f"  - {p}: item removed")
            elif isinstance(a[i], dict) and isinstance(b[i], dict):
                diffs.extend(TestSnapshot._deep_diff(a[i], b[i], p))
            elif isinstance(a[i], list) and isinstance(b[i], list):
                diffs.extend(TestSnapshot._list_diff(a[i], b[i], p))
            elif a[i] != b[i]:
                diffs.append(
                    f"  ~ {p}: {repr(a[i])[:120]} != {repr(b[i])[:120]}"
                )
        return diffs
