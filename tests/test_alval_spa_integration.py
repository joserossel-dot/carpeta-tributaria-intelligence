from pathlib import Path
import pytest

from src.core.tax_folder_engine import TaxFolderEngine

ALVAL_PDF = Path("/Users/josealfonsorossel/Downloads/Carpeta_Tributaria_Regular (8).pdf")


@pytest.mark.skipif(not ALVAL_PDF.exists(), reason="PDF de prueba ALVAL SPA no disponible en entorno local")
class TestAlvalSpaIntegration:
    @pytest.fixture(scope="class")
    def alval_folder(self):
        engine = TaxFolderEngine(str(ALVAL_PDF))
        return engine.parse()

    def test_contributor_info(self, alval_folder):
        """Verifica la extracción limpia del contribuyente, domicilio y comuna/región."""
        contrib = alval_folder.contributor
        assert contrib is not None
        assert contrib.rut == "76293939-8"
        assert contrib.razon_social == "ALVAL SPA"
        assert contrib.comuna == "PUDAHUEL"
        assert contrib.region == "METROPOLITANA DE SANTIAGO"
        assert "null" not in (contrib.domicilio or "").lower()
        assert contrib.domicilio == "CAMINO RENCA LAMPA 9100 LT.10 a, PUDAHUEL"

    def test_representantes_sin_accionistas(self, alval_folder):
        """Verifica que se capturen los 2 representantes multilínea con actuación 'Cualquiera' y no a los accionistas DAB SPA / AG SPA."""
        corp = alval_folder.corporate_info
        assert corp is not None
        assert corp.forma_actuacion_representantes == "Cualquiera"

        reps = corp.representantes
        assert len(reps) == 2

        nombres = [r.nombre for r in reps]
        assert "IGNACIO JOSE ALLENDES CORREA" in nombres
        assert "DIEGO JOSE VALENZUELA INFANTE" in nombres
        # Verificación estricta de que no se mezclaron accionistas
        assert not any("DAB SPA" in n or "AG SPA" in n for n in nombres)

        ruts = {r.nombre: r.rut for r in reps}
        assert ruts["IGNACIO JOSE ALLENDES CORREA"] == "16369817-K"
        assert ruts["DIEGO JOSE VALENZUELA INFANTE"] == "16371206-7"

        for r in reps:
            assert r.forma_actuacion == "Cualquiera"
            assert r.vigente is True

    def test_f22_multigeneracion_y_perdida(self, alval_folder):
        """Verifica los 3 años F22 con pérdida tributaria negativa en AT 2026 y saldo 305 negativo."""
        assert len(alval_folder.f22) == 3

        f22_by_ano = {f.anio_tributario: f for f in alval_folder.f22}
        assert "2026" in f22_by_ano
        assert "2025" in f22_by_ano
        assert "2024" in f22_by_ano

        # AT 2026
        f26 = f22_by_ano["2026"]
        assert f26.ingresos == 7121034432
        assert f26.ingresos_source_code == "1657"
        assert f26.renta_liquida_imponible == -31382439
        assert f26.rli_source_code == "1695"
        assert f26.resultado_financiero == 103376031
        assert f26.capital_propio_tributario == 1756914649
        assert f26.cpt_source_code in ("1698", "645")
        assert f26.saldo_liquidacion_anual == -24086464

        # AT 2025
        f25 = f22_by_ano["2025"]
        assert f25.ingresos == 5850948753
        assert f25.ingresos_source_code == "1657"
        assert f25.renta_liquida_imponible == 13525934
        assert f25.rli_source_code == "1694"
        assert f25.resultado_financiero == 70651986
        assert f25.capital_propio_tributario == 1716248257
        assert f25.cpt_source_code in ("1698", "645")

        # AT 2024
        f24 = f22_by_ano["2024"]
        assert f24.ingresos == 5112917380
        assert f24.ingresos_source_code == "1657"
        assert f24.renta_liquida_imponible == 230291714
        assert f24.rli_source_code == "1694"
        assert f24.resultado_financiero == 176661212
        assert f24.capital_propio_tributario == 568044045
        assert f24.cpt_source_code in ("1698", "645")

    def test_f29_continuity(self, alval_folder):
        """Verifica que se procesen los 36 meses continuos de F29."""
        assert len(alval_folder.monthly_taxes) == 36

    def test_regla_comite_rechazo_perdida(self, alval_folder):
        """Verifica la regla estricta de comité: pérdida tributaria genera Línea = 0 y veredicto explicativo."""
        cr = alval_folder.credit_risk
        assert cr is not None
        assert cr.score_compuesto == 77
        assert cr.decision.desempeno_tributario_texto == "Desempeño Tributario Moderado (Bloqueo por Pérdida F22)"
        assert cr.linea_maxima_sugerida == 0
        assert cr.linea_inicial_sugerida == 0
        assert cr.veredicto == "SIN LÍNEA AUTOMÁTICA (Pérdida Tributaria en F22 — Evaluación Manual con EE.FF.)"

        mem = cr.decision.memoria_calculo
        assert mem["rli_declarada_le_zero"] is True
        assert mem["freno_absorcion_operacional"] == 0.0
        assert mem["linea_maxima_condicionada"] == 0

    def test_volcado_verificacion_nativa_pdfplumber(self):
        """Extrae directamente con pdfplumber (capa nativa sin OCR) y verifica con asserts exactos

        los 12 códigos F22 de ALVAL SPA: 1657, 1690, 1694, 1695, 645, 1698, 843, 844, 1113, 36, 1904 y 305.
        """
        import re
        import pdfplumber

        results = {}
        with pdfplumber.open(ALVAL_PDF) as pdf:
            f22_pages = {
                "2026": [39, 40],
                "2025": [41, 42],
                "2024": [43, 44],
            }
            for at, pages in f22_pages.items():
                lines = []
                for p in pages:
                    txt = pdf.pages[p - 1].extract_text() or ""
                    lines.extend(txt.split("\n"))

                data = {}
                for line in lines:
                    m = re.search(r"1657\s+Ingresos del giro[^\d]*(\d+)", line)
                    if m: data["1657"] = int(m.group(1))

                    m = re.search(r"1672\s+Resultado financiero\s+([\d\.]+)", line)
                    if m: data["1672"] = int(m.group(1).replace(".", ""))

                    if "1690" in line:
                        m = re.search(r"1690\s+Renta líquida[^\-\d]*(-?[\d\.]+)", line)
                        if not m:
                            m = re.search(r"1690.*?\s(-?[\d\.]+)\s*$", line)
                        if m: data["1690"] = int(m.group(1).replace(".", ""))

                    m = re.search(r"1694\s+Renta líquida[^\d]*([\d\.]+)", line)
                    if m: data["1694"] = int(m.group(1).replace(".", ""))

                    m = re.search(r"1695\s+Pérdida tributaria.*?(?:al\s+\d+\s+de\s+[a-záéíóú]+\s+)?([\d\.]+)", line, re.IGNORECASE)
                    if m:
                        val_str = m.group(1).replace(".", "")
                        if val_str != "31":
                            data["1695"] = int(val_str)
                        else:
                            m_end = re.search(r"1695.*?\s([\d\.]+)\s*$", line)
                            if m_end: data["1695"] = int(m_end.group(1).replace(".", ""))

                    m = re.search(r"645\s+CPT positivo final\s+([\d\.]+)", line)
                    if m: data["645"] = int(m.group(1).replace(".", ""))

                    m = re.search(r"1698\s+CPT positivo final[^\d]*14\)\s+([\d\.]+)", line)
                    if not m: m = re.search(r"1698\s+CPT positivo final[^\d]*\)\s+([\d\.]+)", line)
                    if m: data["1698"] = int(m.group(1).replace(".", ""))

                    m = re.search(r"843\s+Patrimonio financiero\s+([\d\.]+)", line)
                    if m: data["843"] = int(m.group(1).replace(".", ""))

                    m = re.search(r"844[^\d]+([\d\.]+)\s*$", line)
                    if m: data["844"] = int(m.group(1).replace(".", ""))

                    m = re.search(r"1113.*?de\s+([\d\.]+)\s+114", line)
                    if m: data["1113"] = int(m.group(1).replace(".", ""))

                    m = re.search(r"36\s+PPM y remanente[^\d]*([\d\.]+)", line)
                    if m: data["36"] = int(m.group(1).replace(".", ""))

                    m = re.search(r"1904.*?\s([\d\.]+)\s*$", line)
                    if m: data["1904"] = int(m.group(1).replace(".", ""))

                    m = re.search(r"305\s+RESULTADO LIQUIDACIÓN[^\-\d]*(-?[\d\.]+)", line)
                    if not m: m = re.search(r"305.*?NTA[^\-\d]*(-?[\d\.]+)", line)
                    if m: data["305"] = int(m.group(1).replace(".", ""))

                results[at] = data

        # Imprimir tabla exacta en consola para informe de auditoría
        print("\n" + "=" * 80)
        print("VOLCADO DE VERIFICACIÓN NATIVA (pdfplumber) — ALVAL SPA (RUT 76.293.939-8)")
        print("=" * 80)
        header = f"{'Código F22':<12} | {'AT 2026':>18} | {'AT 2025':>18} | {'AT 2024':>18}"
        print(header)
        print("-" * len(header))
        target_codes = ["1657", "1672", "1690", "1694", "1695", "645", "1698", "843", "844", "1113", "36", "1904", "305"]
        for c in target_codes:
            v26 = f"${results['2026'].get(c):,}".replace(",", ".") if results['2026'].get(c) is not None else "— (N/A)"
            v25 = f"${results['2025'].get(c):,}".replace(",", ".") if results['2025'].get(c) is not None else "— (N/A)"
            v24 = f"${results['2024'].get(c):,}".replace(",", ".") if results['2024'].get(c) is not None else "— (N/A)"
            print(f"Cód. {c:<7} | {v26:>18} | {v25:>18} | {v24:>18}")
        print("=" * 80)

        # Verificaciones exactas AT 2026
        assert results["2026"]["1657"] == 7_121_034_432
        assert results["2026"]["1672"] == 103_376_031
        assert results["2026"]["1690"] in (31_382_439, -31_382_439)
        assert "1694" not in results["2026"] or results["2026"]["1694"] is None
        assert results["2026"]["1695"] == 31_382_439
        assert results["2026"]["645"] == 1_756_914_649
        assert results["2026"]["1698"] == 1_756_914_649
        assert results["2026"]["843"] == 1_752_776_382
        assert results["2026"]["844"] == 2_030_391_500
        assert "1113" not in results["2026"] or results["2026"]["1113"] in (None, 0)
        assert results["2026"]["36"] == 25_456_103
        assert results["2026"]["1904"] == 25_456_103
        assert results["2026"]["305"] == -24_086_464

        # Verificaciones exactas AT 2025
        assert results["2025"]["1657"] == 5_850_948_753
        assert results["2025"]["1672"] in (70_651_986, 70_651_980)
        assert results["2025"]["1690"] == 13_525_934
        assert results["2025"]["1694"] == 13_525_934
        assert "1695" not in results["2025"] or results["2025"]["1695"] is None
        assert results["2025"]["645"] == 1_716_248_257
        assert results["2025"]["1698"] == 1_716_248_257
        assert results["2025"]["843"] == 1_119_422_984
        assert results["2025"]["844"] in (1_685_487_769, 1_685_487_789)
        assert results["2025"]["1113"] == 3_652_002
        assert results["2025"]["36"] == 62_929_804
        assert results["2025"]["1904"] == 62_929_804
        assert results["2025"]["305"] == -59_241_087

        # Verificaciones exactas AT 2024
        assert results["2024"]["1657"] == 5_112_917_380
        assert results["2024"]["1672"] == 176_661_212
        assert results["2024"]["1690"] == 230_291_714
        assert results["2024"]["1694"] == 230_291_714
        assert "1695" not in results["2024"] or results["2024"]["1695"] is None
        assert results["2024"]["645"] == 568_044_045
        assert results["2024"]["1698"] == 568_044_045
        assert results["2024"]["843"] == 760_735_516
        assert results["2024"]["844"] == 686_264_642
        assert results["2024"]["1113"] == 62_178_763
        assert results["2024"]["36"] == 37_300_652
        assert results["2024"]["1904"] == 37_300_652
        assert results["2024"]["305"] == 24_878_111

    def test_generacion_pdf_alval_spa_layout(self, alval_folder):
        """Genera el PDF y valida los textos clave, códigos F22 y glosas de la versión v2.7.1."""
        import io
        import pdfplumber
        from src.reports.pdf_report import PDFReport

        pdf_bytes = PDFReport().generate(alval_folder)
        assert len(pdf_bytes) > 10_000

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            assert len(pdf.pages) == 2
            text_p1 = pdf.pages[0].extract_text()
            assert "(v2.9.0)" in text_p1
            assert "SIN LÍNEA AUTOMÁTICA" in text_p1
            assert "77 / 100" in text_p1 or "77 pts" in text_p1
            assert "No constituye rating de solvencia" in text_p1
            assert "sujeto a Dicom y Balance" in text_p1
            assert "Pérdida Tributaria en último F22" in text_p1
            assert "2 representante(s) registrado(s)" in text_p1
            assert "Cualquiera" in text_p1
            assert "CAMINO RENCA LAMPA 9100 LT.10 a, PUDAHUEL" in text_p1
            assert "+11.0%" in text_p1
            assert "alta volatilidad mensual" in text_p1
            assert "CV: 24.1%" in text_p1
            assert "Rango:" in text_p1
            assert "M$ 402.100 a M$ 911.478" in text_p1
            assert "Margen operacional ajustado" in text_p1
            assert "Ratio Débito/Crédito Giro 12M: 1.11x" in text_p1
            assert "Ventas/Compras Giro 12M: 1.07x" in text_p1
            assert "RLI AT 2026: -M$ 31.382" in text_p1
            assert "Utilidad Contable s/Balance Cód. 1672" in text_p1
            assert "+M$ 103.376" in text_p1
            assert "CPT: M$ 1.756.915" in text_p1
            assert "incrementado por aporte Cód. 844" in text_p1
            assert "utilidades retenidas" in text_p1
            assert "Penalización -9" in text_p1
            assert "RLI <= 0" in text_p1
            assert "0 de 36 períodos con mora Cód. 94" in text_p1
            assert "5 de últ. 12M sin IVA a pagar" in text_p1

            text_p2 = pdf.pages[1].extract_text()
            full_text = text_p1 + "\n" + text_p2
            assert "Alerta de Overtrading y Deterioro Multianual de Margen" in full_text
            assert "compras superan a las ventas en 6" in full_text
            assert "últimos 12 meses (incluidos mayo y junio 2026)" in full_text
            assert "inyección de Capital Aportado Cód. 844" in full_text
            assert "Ingresos Giro Cód. 1657" in text_p2
            assert "RLI / Pérdida Cód. 1694/1695" in text_p2
            assert "Capital Propio CPT Cód. 645/1698" in text_p2
            assert "-M$ 31.382 (Cód. 1695)" in text_p2
            assert "M$ 13.526 (Cód. 1694)" in text_p2
            assert "M$ 230.292 (Cód. 1694)" in text_p2
            assert "M$ 1.756.915" in text_p2
            assert "M$ 1.716.248" in text_p2
            assert "M$ 568.044" in text_p2
            assert "2025-07 M$ 911.478 M$ 971.150 M$ 173.181" in text_p2
            assert "1.4% s/base" in text_p2
            assert "F22 — CONCILIADO (<10% dif.)" in text_p2
            assert "s/base F29" not in text_p2
            assert "CONCILIADO (<10% dif.)" in text_p2
            assert "Motor Determinista Cavilaria v2.9.0" in text_p2
