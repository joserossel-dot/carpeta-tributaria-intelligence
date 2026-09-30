import io
from pathlib import Path
import pdfplumber
import pytest

from src.core.tax_folder_engine import TaxFolderEngine
from src.parsers.f22_parser import F22Parser
from src.reports.pdf_report import PDFReport

NUTRISA_PDF = Path("/Users/josealfonsorossel/Downloads/Carpeta Tributaria Personalizada NUTRISA.pdf")


@pytest.mark.skipif(not NUTRISA_PDF.exists(), reason="PDF de prueba NUTRISA no disponible en entorno local")
class TestGoldenNutrisa:
    @pytest.fixture(scope="class")
    def nutrisa_folder(self):
        engine = TaxFolderEngine(str(NUTRISA_PDF))
        return engine.parse()

    def test_representantes_multilinea_y_forma_actuacion(self, nutrisa_folder):
        """Verifica la extracción limpia de los 3 representantes de NUTRISA, incluyendo el multilínea y la forma de actuación."""
        corp = nutrisa_folder.corporate_info
        assert corp is not None
        assert corp.forma_actuacion_representantes == "En conjunto"

        reps = corp.representantes
        assert len(reps) == 3

        nombres = [r.nombre for r in reps]
        assert "HECTOR GABRIEL RIOS LARRAIN" in nombres
        assert "MARIA GLORIA RIOS LARRAIN" in nombres
        # Verificación estricta de que no se trunca el segundo apellido "CASANUEVA"
        assert "JOSE LUIS RODRIGUEZ CASANUEVA" in nombres
        assert not any("JOSE LUIS RODRIGUEZ\n" in n for n in nombres)

        ruts = {r.nombre: r.rut for r in reps}
        assert ruts["HECTOR GABRIEL RIOS LARRAIN"] == "4506112-4"
        assert ruts["MARIA GLORIA RIOS LARRAIN"] == "4509405-7"
        assert ruts["JOSE LUIS RODRIGUEZ CASANUEVA"] == "10958716-8"

        for r in reps:
            assert r.forma_actuacion == "En conjunto"
            assert r.vigente is True

    def test_evaluacion_crediticia_v26_perfil_solido(self, nutrisa_folder):
        """Verifica la clasificación v2.9, puntaje y líneas escalonadas para NUTRISA."""
        cr = nutrisa_folder.credit_risk
        assert cr is not None
        assert cr.score_crediticio is not None
        assert cr.score_crediticio == 92
        assert cr.evaluacion_referencial == "ELEGIBLE PARA LÍNEA COMERCIAL (FASE 1 TRIBUTARIA) (Línea Sujeta a Dicom)"
        assert cr.clasificacion_riesgo == "ELEGIBLE PARA LÍNEA COMERCIAL (FASE 1 TRIBUTARIA)"
        assert cr.desempeno_tributario_texto == "Capacidad Operativa Tributaria Alta"

        # Líneas escalonadas: Máxima M$ 14.400, Inicial M$ 7.200 (50% apertura)
        assert cr.linea_maxima_condicionada == 14_400_000
        assert cr.linea_inicial_sugerida == 7_200_000
        assert cr.cupo_aprobado == 7_200_000
        assert cr.plazo_inicial_sugerido == "15 días (o 30 días con 50% de anticipo)"

    def test_memoria_calculo_nutrisa(self, nutrisa_folder):
        """Verifica la consistencia cuantitativa de la Memoria de Cálculo."""
        mem = nutrisa_folder.credit_risk.memoria_calculo
        assert mem is not None

        # Freno B2 debe ser min(15% Spread F29, 25% RLI Mensualizada F22)
        # 25% RLI Mensualizada: 0.25 * (692.055.540 / 12) = 14.417.824
        # Techo B1: 8% Compras = 28.162.864
        # Freno flujo < Techo compras -> el freno gobierna
        assert mem["rli_ultimo_f22"] == 692_055_540
        assert mem["capital_propio_tributario"] == 3_625_109_624
        assert mem["base_compras_c_base"] == 523_884_831
        assert mem["techo_operativo_8pct"] == 41_910_786
        assert mem["freno_absorcion_operacional"] == 14_417_824
        assert mem["linea_maxima_condicionada"] == 14_400_000
        assert mem["linea_inicial_sugerida"] == 7_200_000

        # CPT holgado (Tope patrimonial 3% CPT no restrictivo)
        assert mem["tope_patrimonial_3pct_cpt"] == 108_753_289

    def test_filtro_elegibilidad_y_resguardo_nutrisa(self, nutrisa_folder):
        """Verifica que el filtro de elegibilidad y resguardo incluyan la actuación conjunta y representantes."""
        cr = nutrisa_folder.credit_risk
        filtro = cr.filtro_elegibilidad
        rep_filtro = next((item for item in filtro if "Representantes Legales" in item.get("parametro", "")), None)
        assert rep_filtro is not None
        assert "En conjunto" in rep_filtro.get("detalle", "")
        assert "3 representante(s) registrado(s)" in rep_filtro.get("detalle", "")

        resguardo = cr.resguardo_comercial_sugerido
        assert "En conjunto" in resguardo
        assert "HECTOR GABRIEL RIOS LARRAIN" in resguardo
        assert "MARIA GLORIA RIOS LARRAIN" in resguardo
        assert "JOSE LUIS RODRIGUEZ CASANUEVA" in resguardo

        # Verificación de Pilares 1, 3, 4 y 5
        desglose = cr.desglose_score
        p1 = next(p for p in desglose if "Continuidad" in p.nombre)
        assert p1.puntaje_obtenido == 15
        assert "23 meses continuos declarados (2024-06 a 2026-04) sin lagunas tributarias" in p1.detalle

        p3 = next(p for p in desglose if "Holgura Débito/Crédito IVA (F29)" in p.nombre)
        assert p3 is not None
        assert p3.puntaje_obtenido == 20
        assert "Ratio Débito / Crédito Giro 12M: 1.45x" in p3.detalle

        p4 = next(p for p in desglose if "Rentabilidad" in p.nombre)
        assert p4.puntaje_obtenido == 13
        assert "RLI AT 2026: M$ 692.056 (9.1% s/ingresos; Utilidad Contable Cód. 1672: +M$ 656.065) | CPT: M$ 3.625.110 [Tope 13/15 pts: carpeta contiene solo 1 AT de F22, sin serie multianual verificable]" in p4.detalle

        p5 = next(p for p in desglose if "Cumplimiento Fiscal" in p.nombre)
        assert p5.puntaje_obtenido == 15
        assert "0 de 23 períodos F29 con recargos por mora fiscal (Cód. 94) y 0 postergaciones de IVA (Cód. 779)" in p5.detalle

    def test_generacion_pdf_nutrisa_layout(self, nutrisa_folder):
        """Genera el PDF y valida los textos clave de la versión v2.9.0."""
        pdf_bytes = PDFReport().generate(nutrisa_folder)
        assert len(pdf_bytes) > 10_000

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text_p1 = pdf.pages[0].extract_text()
            assert "(v2.9.1)" in text_p1
            assert "ELEGIBLE PARA LÍNEA COMERCIAL" in text_p1
            assert "Inicial: M$ 7.200" in text_p1
            assert "Máxima: M$ 14.400" in text_p1
            assert "En conjunto" in text_p1
            assert "Tope de concentración por proveedor: 3% CPT" in text_p1
            # Normalización de domicilio
            assert "01565 Bodeg" in text_p1
            # Aclaración de glosa Paso B2
            assert "(Proxy tributario sobre RLI/12; no equivale a flujo de caja libre)" in text_p1
            # Glosa Apertura con tramos
            assert "50% de Apertura para Score >=85" in text_p1

            if len(pdf.pages) > 1:
                text_p2 = pdf.pages[1].extract_text()
                assert "Ingresos Giro Cód. 1657" in text_p2
                assert "RLI / Pérdida Cód. 1694/1695" in text_p2
                assert "Capital Propio CPT Cód. 645/1698" in text_p2
                assert "M$ 692.056 (Cód. 1694)" in text_p2
                assert "M$ 3.625.110" in text_p2
                assert "Motor Determinista Cavilaria v2.9.1" in text_p2
                # Base única de conciliación F22
                assert "3.2% s/base" in text_p2
                assert "F22 — CONCILIADO (<10% dif.)" in text_p2
                assert "s/base F29" not in text_p2

    def test_volcado_verificacion_nativa_nutrisa_pdfplumber(self):
        """Extrae directamente con pdfplumber y verifica con asserts exactos los códigos F22 de NUTRISA."""
        results = {}
        target_codes = ["1657", "1672", "1690", "1694", "1695", "645", "1698", "843", "844", "1113", "36", "1904", "305"]
        with pdfplumber.open(NUTRISA_PDF) as pdf:
            # En NUTRISA F22 está en las últimas páginas (ej. pág 25-26)
            full_txt = "\n".join(p.extract_text() or "" for p in pdf.pages[24:])
            data = {}
            for c in target_codes:
                val, _ = F22Parser._extract_raw_code(full_txt, c)
                data[c] = val
            results["2026"] = data

        print("\n" + "=" * 80)
        print("VOLCADO DE VERIFICACIÓN NATIVA (pdfplumber) — NUTRISA (RUT 95.214.000-0)")
        print("=" * 80)
        header = f"{'Código F22':<12} | {'AT 2026':>18}"
        print(header)
        print("-" * len(header))
        for c in target_codes:
            v26 = f"${results['2026'].get(c):,}".replace(",", ".") if results['2026'].get(c) is not None else "— (N/A)"
            print(f"Cód. {c:<7} | {v26:>18}")
        print("=" * 80)

        assert results["2026"]["1657"] == 7_609_347_772
        assert results["2026"]["1672"] == 656_064_546
        assert results["2026"]["1690"] == 692_055_540
        assert results["2026"]["1694"] == 692_055_540
        assert "1695" not in results["2026"] or results["2026"]["1695"] is None
        assert results["2026"]["645"] == 3_625_109_624
        assert results["2026"]["1698"] == 3_625_109_624
        assert results["2026"]["843"] == 1_916_468_561
        assert "844" not in results["2026"] or results["2026"]["844"] is None
        assert results["2026"]["1113"] == 186_854_996
        assert results["2026"]["36"] == 83_017_357
        assert results["2026"]["1904"] == 83_017_357
        assert results["2026"]["305"] == 103_837_639
