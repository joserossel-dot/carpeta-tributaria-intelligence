import subprocess
import sys
from pathlib import Path

import typer
from typer.testing import CliRunner

from src.cli import cli

runner = CliRunner()


class TestCli:
    def _invoke(self, args: list[str]):
        return runner.invoke(cli, args, color=False)

    def _output(self, result) -> str:
        return result.output

    def test_help(self) -> None:
        result = self._invoke(["--help"])
        assert result.exit_code == 0
        assert "carpeta-tributaria" in self._output(result)
        assert "parse" in self._output(result)
        assert "analyze" in self._output(result)
        assert "export" in self._output(result)
        assert "benchmark" in self._output(result)

    def test_parse_valid_pdf(self) -> None:
        result = self._invoke(["parse", "examples/CPTAgrGonzalezLtda.pdf"])
        assert result.exit_code == 0
        assert "RUT:" in self._output(result)
        assert "F29:" in self._output(result)
        assert "Actividades:" in self._output(result)

    def test_parse_invalid_path(self) -> None:
        result = self._invoke(["parse", "no_existe.pdf"])
        assert result.exit_code == 1
        assert "Error:" in self._output(result)

    def test_export_json(self) -> None:
        out = "output/test_export.json"
        result = self._invoke(["export", "examples/CPTAgrGonzalezLtda.pdf", "--output", out])
        assert result.exit_code == 0
        assert Path(out).exists()
        assert "Exportado:" in self._output(result)
        Path(out).unlink(missing_ok=True)

    def test_export_unsupported_format(self) -> None:
        result = self._invoke(["export", "examples/CPTAgrGonzalezLtda.pdf", "--format", "csv"])
        assert result.exit_code == 1
        assert "Error:" in self._output(result)

    def test_analyze_generates_output(self) -> None:
        result = self._invoke(["analyze", "examples/CPTAgrGonzalezLtda.pdf"])
        assert result.exit_code == 0
        assert "JSON:" in self._output(result)
        assert "Reporte:" in self._output(result)
        assert Path("output/data.json").exists()
        assert Path("output/report.md").exists()

    def test_benchmark_directory(self) -> None:
        result = self._invoke(["benchmark", "examples/"])
        assert result.exit_code == 0
        assert "exitosos" in self._output(result)

    def test_benchmark_invalid_dir(self) -> None:
        result = self._invoke(["benchmark", "no_existe/"])
        assert result.exit_code == 1
        assert "Error:" in self._output(result)

    def test_parse_all_valid_pdfs(self) -> None:
        pdfs = [
            "CPTAgrGonzagriLtda.pdf",
            "CPTAgrGonzalezLtda.pdf",
            "CPTExportadora.pdf",
            "CPTGonzagriS.A..pdf",
            "Carpeta Tributaria.CLINICA HYPERBARIC.pdf",
        ]
        for pdf in pdfs:
            result = self._invoke(["parse", f"examples/{pdf}"])
            assert result.exit_code == 0, f"Failed on {pdf}: {self._output(result)}"


class TestCliInstalled:

    def test_entry_point(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "carpeta-tributaria" in result.stdout or "src.cli" in result.stdout
