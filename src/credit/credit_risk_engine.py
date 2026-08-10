from src.credit.sector_benchmark import SectorBenchmark
from src.models.activity import Activity
from src.models.credit_risk import (
    CalidadDatos,
    CaminoMitigacion,
    CampoNoConfiable,
    ComposicionVentas,
    CreditRiskResult,
    Decision,
    Hechos,
    Indicadores,
    MargenVsGiro,
    MoraEfectiva,
    PostergacionesIva,
    RespaldoEstructural,
)
from src.models.tax_folder import TaxFolder

MESES_MINIMOS_PARA_SCORING = 6


class CreditRiskEngine:
    """Motor de decisión crediticia B2B.

    Principio de diseño (acordado explícitamente con el usuario, no
    inventado por el motor): se separan HECHOS (datos que se reportan tal
    cual, sin juicio -- composición de ventas, uso de postergación de
    IVA) de INDICADORES (datos que sí sostienen una evaluación de riesgo
    -- mora efectiva, margen vs. giro, respaldo estructural). Los hechos
    nunca entran al score compuesto; se usan como condiciones para los
    caminos de mitigación.
    """

    def __init__(self, benchmark: SectorBenchmark | None = None):
        self.benchmark = benchmark or SectorBenchmark()

    def calculate(
        self, tax_folder: TaxFolder, cupo_solicitado: int | None = None
    ) -> CreditRiskResult:
        calidad = self._evaluar_calidad_datos(tax_folder)
        hechos = self._extraer_hechos(tax_folder)

        if calidad.veredicto != "APTO_PARA_SCORING":
            return CreditRiskResult(calidad_datos=calidad, hechos=hechos)

        indicadores = self._calcular_indicadores(tax_folder, cupo_solicitado)
        score_compuesto = self._componer_score(indicadores)
        decision = self._decidir(hechos, indicadores, score_compuesto, cupo_solicitado)
        alertas, fortalezas = self._alertas_y_fortalezas(hechos, indicadores)

        return CreditRiskResult(
            calidad_datos=calidad,
            hechos=hechos,
            indicadores=indicadores,
            score_compuesto=score_compuesto,
            decision=decision,
            alertas=alertas,
            fortalezas=fortalezas,
        )

    # ------------------------------------------------------------------
    # Calidad de datos (gate obligatorio)
    # ------------------------------------------------------------------
    def _evaluar_calidad_datos(self, tax_folder: TaxFolder) -> CalidadDatos:
        campos_no_confiables = [
            CampoNoConfiable(campo=f"f22.{f.anio_tributario}.{obs_campo}", motivo=obs)
            for f in tax_folder.f22
            for obs in f.observaciones
            for obs_campo in [self._campo_desde_observacion(obs)]
        ]

        meses_f29 = len(tax_folder.monthly_taxes)
        tiene_cpt = any(f.capital_propio_tributario is not None for f in tax_folder.f22)

        checks = {
            "contribuyente": tax_folder.contributor is not None
            and tax_folder.contributor.razon_social is not None,
            "f29_suficientes": meses_f29 >= MESES_MINIMOS_PARA_SCORING,
            "f22_con_cpt": tiene_cpt,
        }
        completitud_pct = round(100 * sum(checks.values()) / len(checks), 1)

        if checks["f29_suficientes"] and checks["contribuyente"]:
            veredicto = "APTO_PARA_SCORING"
        else:
            veredicto = "DATOS_INSUFICIENTES"

        return CalidadDatos(
            completitud_pct=completitud_pct,
            campos_no_confiables=campos_no_confiables,
            meses_f29_faltantes=[],
            veredicto=veredicto,
        )

    @staticmethod
    def _campo_desde_observacion(observacion: str) -> str:
        if observacion.startswith(("No se encontró", "No se encontraron")):
            return (
                observacion.replace("No se encontró", "")
                .replace("No se encontraron", "")
                .strip()
            )
        if "Impuesto determinado" in observacion:
            return "Impuesto determinado"
        return observacion[:40].strip()

    # ------------------------------------------------------------------
    # Hechos (sin calificar)
    # ------------------------------------------------------------------
    def _extraer_hechos(self, tax_folder: TaxFolder) -> Hechos:
        return Hechos(
            composicion_ventas=self._composicion_ventas(tax_folder),
            postergaciones_iva=self._postergaciones_iva(tax_folder),
        )

    @staticmethod
    def _composicion_ventas(tax_folder: TaxFolder) -> ComposicionVentas:
        facturado = 0
        boletas = 0
        for f29 in tax_folder.f29:
            for det in f29.detalles:
                if det.codigo == "502":
                    facturado += _parse_monto(det.valor)
                elif det.codigo == "111":
                    boletas += _parse_monto(det.valor)

        total = facturado + boletas
        nota = None
        if boletas == 0 and facturado > 0:
            nota = (
                "sin código 111 (boletas) detectado -- puede ser un giro 100% "
                "facturado, o el rubro simplemente no emite boletas; no "
                "confirmar sin cruzar con el giro real de la empresa"
            )

        return ComposicionVentas(
            pct_facturado=round(facturado / total, 4) if total else None,
            pct_boletas=round(boletas / total, 4) if total else None,
            monto_facturado_estimado=facturado or None,
            meses_evaluados=len(tax_folder.f29),
            nota=nota,
        )

    @staticmethod
    def _postergaciones_iva(tax_folder: TaxFolder) -> PostergacionesIva:
        periodos = []
        for f29 in tax_folder.f29:
            for det in f29.detalles:
                if det.codigo == "779" and _parse_monto(det.valor) > 0:
                    periodos.append(f29.periodo)
                    break

        return PostergacionesIva(
            meses_con_postergacion=len(periodos),
            total_meses_evaluados=len(tax_folder.f29),
            periodos=periodos,
        )

    # ------------------------------------------------------------------
    # Indicadores (sí se califican)
    # ------------------------------------------------------------------
    def _calcular_indicadores(
        self, tax_folder: TaxFolder, cupo_solicitado: int | None
    ) -> Indicadores:
        return Indicadores(
            mora_efectiva=self._mora_efectiva(tax_folder),
            margen_vs_giro=self._margen_vs_giro(tax_folder),
            respaldo_estructural=self._respaldo_estructural(tax_folder, cupo_solicitado),
        )

    @staticmethod
    def _mora_efectiva(tax_folder: TaxFolder) -> MoraEfectiva:
        meses_con_recargo = 0
        meses_con_remanente = 0
        for f29 in tax_folder.f29:
            for det in f29.detalles:
                if det.codigo == "94" and _parse_monto(det.valor) > 0:
                    meses_con_recargo += 1
                if det.codigo == "504" and _parse_monto(det.valor) > 0:
                    meses_con_remanente += 1

        n = len(tax_folder.f29)
        if n == 0:
            return MoraEfectiva(confianza="sin_datos")

        pct_mora = meses_con_recargo / n
        score = round(max(0, 100 - pct_mora * 100 * 4))  # cada mes de mora pesa 4x
        confianza = "alta" if n >= 12 else "media" if n >= 6 else "baja"

        return MoraEfectiva(
            score=score,
            meses_con_recargo=meses_con_recargo,
            meses_con_remanente_credito=meses_con_remanente,
            meses_evaluados=n,
            confianza=confianza,
        )

    def _margen_vs_giro(self, tax_folder: TaxFolder) -> MargenVsGiro:
        last_12 = tax_folder.monthly_taxes[-12:] if len(tax_folder.monthly_taxes) >= 12 else tax_folder.monthly_taxes
        debitos = [m.debito_fiscal for m in last_12 if m.debito_fiscal is not None]
        creditos = [m.credito_fiscal for m in last_12 if m.credito_fiscal is not None]

        ratio = None
        if debitos and creditos and sum(creditos) > 0:
            ratio = round(float(sum(debitos) / sum(creditos)), 3)

        actividad = _actividad_principal(tax_folder.activities)
        codigo_actividad = actividad.codigo if actividad else None
        descripcion = actividad.descripcion if actividad else None

        ratio_promedio, n_empresas = self.benchmark.lookup(codigo_actividad)

        score = None
        confianza = "sin_datos"
        if ratio is not None:
            if ratio_promedio:
                relativo = ratio / ratio_promedio
                score = round(min(100, max(0, relativo * 70)))
                confianza = "alta"
            else:
                confianza = "insuficiente_muestra"

        return MargenVsGiro(
            score=score,
            ratio_debito_credito_12m=ratio,
            codigo_actividad=codigo_actividad,
            descripcion_actividad=descripcion,
            ratio_promedio_sector=ratio_promedio,
            n_empresas_referencia=n_empresas,
            confianza=confianza,
        )

    @staticmethod
    def _respaldo_estructural(
        tax_folder: TaxFolder, cupo_solicitado: int | None
    ) -> RespaldoEstructural:
        f22_ordenados = sorted(
            (f for f in tax_folder.f22 if f.capital_propio_tributario is not None),
            key=lambda f: f.anio_tributario or "",
            reverse=True,
        )
        if not f22_ordenados:
            return RespaldoEstructural(confianza="sin_datos")

        cpt = f22_ordenados[0].capital_propio_tributario
        veces = None
        score = None
        if cupo_solicitado and cupo_solicitado > 0 and cpt is not None:
            veces = round(cpt / cupo_solicitado, 2)
            score = round(min(100, max(0, veces * 25)))

        return RespaldoEstructural(
            score=score,
            capital_propio_tributario=cpt,
            cupo_solicitado=cupo_solicitado,
            veces_cobertura=veces,
            confianza="media" if cpt is not None else "sin_datos",
        )

    # ------------------------------------------------------------------
    # Composición final
    # ------------------------------------------------------------------
    MIN_INDICADORES_PARA_COMPUESTO = 2

    @staticmethod
    def _componer_score(indicadores: Indicadores) -> int | None:
        scores = [
            s.score
            for s in (
                indicadores.mora_efectiva,
                indicadores.margen_vs_giro,
                indicadores.respaldo_estructural,
            )
            if s.score is not None
        ]
        if len(scores) < CreditRiskEngine.MIN_INDICADORES_PARA_COMPUESTO:
            # Un solo indicador disponible no es un "compuesto" -- mostrarlo
            # como si lo fuera da una falsa sensación de certeza.
            return None
        return round(sum(scores) / len(scores))

    @staticmethod
    def _decidir(
        hechos: Hechos,
        indicadores: Indicadores,
        score_compuesto: int | None,
        cupo_solicitado: int | None,
    ) -> Decision:
        if score_compuesto is None:
            resultado_base = "NO_EVALUABLE"
        elif score_compuesto >= 70:
            resultado_base = "APROBADO"
        elif score_compuesto >= 50:
            resultado_base = "APROBADO_CON_CONDICIONES"
        else:
            resultado_base = "RECHAZADO"

        caminos: list[CaminoMitigacion] = []

        alto_facturado = (hechos.composicion_ventas.pct_facturado or 0) > 0.7
        caminos.append(
            CaminoMitigacion(
                condicion="cesion_facturas_factoring",
                aplica=alto_facturado,
                resultado="APROBADO" if alto_facturado else "NO_APLICA",
                cupo_sugerido=cupo_solicitado if alto_facturado else None,
                justificacion=(
                    "alta proporción facturada permite ceder cuentas por "
                    "cobrar como garantía, reduciendo el riesgo de cobranza "
                    "independiente del score de margen"
                    if alto_facturado
                    else "proporción facturada insuficiente para estructurar factoring"
                ),
            )
        )

        mora_sana = (indicadores.mora_efectiva.score or 0) >= 85
        caminos.append(
            CaminoMitigacion(
                condicion="pago_contado_con_descuento",
                aplica=mora_sana,
                resultado="APROBADO" if mora_sana else "NO_APLICA",
                justificacion=(
                    "sin señales de mora efectiva en el historial evaluado"
                    if mora_sana
                    else "historial de mora insuficiente para ofrecer esta vía sin garantía adicional"
                ),
            )
        )

        return Decision(
            resultado_base=resultado_base,
            producto_evaluado="credito_30_dias",
            caminos_mitigacion=caminos,
        )

    @staticmethod
    def _alertas_y_fortalezas(
        hechos: Hechos, indicadores: Indicadores
    ) -> tuple[list[str], list[str]]:
        alertas = []
        fortalezas = []

        if indicadores.mora_efectiva.meses_con_recargo > 0:
            alertas.append(
                f"{indicadores.mora_efectiva.meses_con_recargo} mes(es) con recargo/interés "
                "por mora efectiva en el período evaluado"
            )
        elif indicadores.mora_efectiva.meses_evaluados > 0:
            fortalezas.append(
                f"Cero meses con mora efectiva en {indicadores.mora_efectiva.meses_evaluados} "
                "meses de historia evaluados"
            )

        if indicadores.margen_vs_giro.confianza == "insuficiente_muestra":
            alertas.append(
                "Margen vs. giro sin benchmark confiable todavía "
                f"(muestra actual: {indicadores.margen_vs_giro.n_empresas_referencia} empresas del rubro)"
            )

        if indicadores.respaldo_estructural.veces_cobertura is not None:
            if indicadores.respaldo_estructural.veces_cobertura < 1:
                alertas.append(
                    "Capital propio tributario por debajo del cupo solicitado"
                )
            elif indicadores.respaldo_estructural.veces_cobertura >= 3:
                fortalezas.append(
                    f"Capital propio tributario cubre {indicadores.respaldo_estructural.veces_cobertura}x "
                    "el cupo solicitado"
                )

        return alertas, fortalezas


def _actividad_principal(activities: list) -> Activity | None:
    for a in activities:
        if isinstance(a, Activity) and a.principal:
            return a
    for a in activities:
        if isinstance(a, Activity):
            return a
    return None


def _parse_monto(valor: str | None) -> int:
    if not valor:
        return 0
    limpio = valor.strip().replace(".", "").replace(",", "")
    if not limpio or limpio == "-":
        return 0
    try:
        return int(limpio)
    except ValueError:
        return 0
