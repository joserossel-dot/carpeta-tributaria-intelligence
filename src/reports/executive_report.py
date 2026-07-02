from src.analyzers.analysis_result import AnalysisResult
from src.kpis.kpi_result import KPIResult
from src.models.tax_folder import TaxFolder


class ExecutiveReport:
    def generate(
        self,
        tax_folder: TaxFolder,
        kpis: KPIResult,
        analysis: AnalysisResult,
    ) -> str:
        lines: list[str] = []

        self._add_header(lines)
        self._add_general_data(lines, tax_folder)
        self._add_principal_activity(lines, kpis)
        self._add_tax_regime(lines, tax_folder)
        self._add_company_age(lines, kpis, tax_folder)
        self._add_f29_summary(lines, kpis, tax_folder)
        self._add_statistics(lines, analysis)
        self._add_alerts(lines, analysis)
        self._add_warnings(lines, analysis)

        return "\n".join(lines)

    @staticmethod
    def _add_header(lines: list[str]) -> None:
        lines.append("# Informe Ejecutivo — Carpeta Tributaria\n")

    @staticmethod
    def _add_general_data(lines: list[str], tf: TaxFolder) -> None:
        lines.append("## Datos Generales\n")
        c = tf.contributor
        lines.append(f"- **RUT:** {c.rut if c and c.rut else 'No disponible'}")
        lines.append(f"- **Razón Social:** {c.razon_social if c and c.razon_social else 'No disponible'}")
        lines.append(f"- **Domicilio:** {c.domicilio if c and c.domicilio else 'No disponible'}")
        lines.append(f"- **Comuna:** {c.comuna if c and c.comuna else 'No disponible'}")
        lines.append(f"- **Región:** {c.region if c and c.region else 'No disponible'}")
        lines.append(f"- **Fecha Generación:** {c.fecha_generacion if c and c.fecha_generacion else 'No disponible'}")
        lines.append(f"- **Inicio Actividades:** {c.fecha_inicio_actividades if c and c.fecha_inicio_actividades else 'No disponible'}")
        lines.append("")

    @staticmethod
    def _add_principal_activity(lines: list[str], kpis: KPIResult) -> None:
        lines.append("## Actividad Principal\n")
        if kpis.principal_activity:
            lines.append(f"{kpis.principal_activity}")
        else:
            lines.append("No disponible")
        lines.append("")

    @staticmethod
    def _add_tax_regime(lines: list[str], tf: TaxFolder) -> None:
        lines.append("## Régimen Tributario\n")
        c = tf.contributor
        if c and c.regimen_tributario:
            lines.append(f"{c.regimen_tributario}")
        else:
            lines.append("No disponible")
        lines.append("")

    @staticmethod
    def _add_company_age(lines: list[str], kpis: KPIResult, tf: TaxFolder) -> None:
        lines.append("## Antigüedad\n")
        if kpis.company_age_years is not None:
            lines.append(f"**{kpis.company_age_years} años**")
            c = tf.contributor
            if c and c.fecha_inicio_actividades:
                lines.append(f"(desde {c.fecha_inicio_actividades})")
        else:
            lines.append("No disponible")
        lines.append("")

    @staticmethod
    def _add_f29_summary(lines: list[str], kpis: KPIResult, tf: TaxFolder) -> None:
        lines.append("## Resumen de F29\n")
        lines.append(f"- **Total declaraciones:** {kpis.f29_count}")
        if kpis.first_f29_period:
            lines.append(f"- **Primer período:** {kpis.first_f29_period}")
        if kpis.last_f29_period:
            lines.append(f"- **Último período:** {kpis.last_f29_period}")
        if kpis.declared_months is not None:
            lines.append(f"- **Meses declarados:** {kpis.declared_months}")
        lines.append("")

    @staticmethod
    def _add_statistics(lines: list[str], analysis: AnalysisResult) -> None:
        lines.append("## Estadísticas\n")
        for key, value in sorted(analysis.statistics.items()):
            label = key.replace("_", " ").capitalize()
            lines.append(f"- **{label}:** {value}")
        lines.append("")

    @staticmethod
    def _add_alerts(lines: list[str], analysis: AnalysisResult) -> None:
        lines.append("## Alertas\n")
        if analysis.alerts:
            for alert in analysis.alerts:
                lines.append(f"- {alert}")
        else:
            lines.append("Sin alertas")
        lines.append("")

    @staticmethod
    def _add_warnings(lines: list[str], analysis: AnalysisResult) -> None:
        lines.append("## Advertencias\n")
        if analysis.warnings:
            for warning in analysis.warnings:
                lines.append(f"- {warning}")
        else:
            lines.append("Sin advertencias")
        lines.append("")
