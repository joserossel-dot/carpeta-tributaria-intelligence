import sys
from pathlib import Path

import typer

from src.core.tax_folder_engine import TaxFolderEngine
from src.exporters.json_exporter import JsonExporter
from src.reports.executive_report import ExecutiveReport

cli = typer.Typer(
    name="carpeta-tributaria",
    help="Motor de inteligencia tributaria para procesar carpetas tributarias del SII",
)


def _resolve_path(path: str) -> Path:
    p = Path(path)
    if not p.exists():
        typer.echo(f"Error: archivo no encontrado: {path}", err=True)
        raise typer.Exit(1)
    return p


@cli.command()
def parse(
    pdf: str = typer.Argument(..., help="Ruta al archivo PDF"),
) -> None:
    """Procesa un PDF y muestra un resumen básico."""
    path = _resolve_path(pdf)
    engine = TaxFolderEngine(str(path))
    result = engine.parse()

    typer.echo(f"Archivo:      {result.metadata.source_file}")
    typer.echo(f"Páginas:      {result.metadata.pages}")
    typer.echo(f"Tiempo:       {result.metadata.processing_time}s")

    if result.contributor:
        typer.echo(f"RUT:          {result.contributor.rut or '—'}")
        typer.echo(f"Razón Social: {result.contributor.razon_social or '—'}")

    typer.echo(f"Actividades:  {len(result.activities)}")
    typer.echo(f"F29:          {len(result.f29)}")
    typer.echo(f"Propiedades:  {len(result.properties)}")
    typer.echo(f"Vehículos:    {len(result.vehicles)}")


@cli.command()
def analyze(
    pdf: str = typer.Argument(..., help="Ruta al archivo PDF"),
) -> None:
    """Procesa un PDF, genera JSON y reporte Markdown en output/."""
    path = _resolve_path(pdf)
    engine = TaxFolderEngine(str(path))
    result = engine.parse()

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    data_path = output_dir / "data.json"
    exporter = JsonExporter(normalize=True)
    exporter.export(result, data_path)
    typer.echo(f"JSON:  {data_path.resolve()}")

    report = ExecutiveReport()
    markdown = report.generate(result, result.kpis, result.analysis)
    report_path = output_dir / "report.md"
    report_path.write_text(markdown, encoding="utf-8")
    typer.echo(f"Reporte: {report_path.resolve()}")


@cli.command()
def export(
    pdf: str = typer.Argument(..., help="Ruta al archivo PDF"),
    format: str = typer.Option("json", "--format", help="Formato de exportación"),
    output: str = typer.Option(None, "--output", "-o", help="Ruta de salida"),
) -> None:
    """Exporta los datos extraídos de un PDF."""
    if format != "json":
        typer.echo(f"Error: formato no soportado: {format}", err=True)
        raise typer.Exit(1)

    path = _resolve_path(pdf)
    engine = TaxFolderEngine(str(path))
    result = engine.parse()

    out = output or f"output/{path.stem}.json"
    exporter = JsonExporter(normalize=True)
    result_path = exporter.export(result, out)
    typer.echo(f"Exportado: {result_path.resolve()}")


@cli.command()
def benchmark(
    directory: str = typer.Argument(".", help="Directorio con archivos PDF"),
) -> None:
    """Ejecuta benchmark sobre todos los PDFs en un directorio."""
    import time as time_mod

    root = Path(directory)
    if not root.is_dir():
        typer.echo(f"Error: directorio no encontrado: {directory}", err=True)
        raise typer.Exit(1)

    pdfs = sorted(root.glob("*.pdf"))
    if not pdfs:
        typer.echo(f"No se encontraron PDFs en {directory}")
        raise typer.Exit(1)

    ok = fail = 0
    total_time = 0.0

    for pdf in pdfs:
        try:
            t0 = time_mod.perf_counter()
            engine = TaxFolderEngine(str(pdf))
            result = engine.parse()
            elapsed = time_mod.perf_counter() - t0
            total_time += elapsed
            ok += 1
            typer.echo(
                f"  {pdf.name:50s}  {result.metadata.pages:>4} págs  "
                f"{len(result.f29):>3} F29  {elapsed:>7.2f}s"
            )
        except Exception as e:
            fail += 1
            typer.echo(f"  {pdf.name:50s}  ERROR: {e}", err=True)

    n = ok or 1
    typer.echo("")
    typer.echo(f"  {ok} exitosos, {fail} fallidos — {total_time:.1f}s total, {total_time / n:.2f}s promedio")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
