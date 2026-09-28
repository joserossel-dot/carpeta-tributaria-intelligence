import io
from pathlib import Path
import pdfplumber
import pytest

from src.core.tax_folder_engine import TaxFolderEngine
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
        """Verifica la clasificación v2.6, puntaje y líneas escalonadas para NUTRISA."""
        cr = nutrisa_folder.credit_risk
        assert cr is not None
        assert cr.score_crediticio is not None
        assert cr.score_crediticio >= 85
        assert cr.evaluacion_referencial == "PERFIL TRIBUTARIO SÓLIDO (Línea Sujeta a Dicom)"
        assert cr.clasificacion_riesgo == "PERFIL TRIBUTARIO SÓLIDO"
        assert cr.desempeno_tributario_texto == "Desempeño Tributario Alto"

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

        # CPT holgado (Tope patrimonial no restrictivo)
        assert mem["tope_patrimonial_12pct_cpt"] == 435_013_155

    def test_filtro_elegibilidad_y_resguardo_nutrisa(self, nutrisa_folder):
        """Verifica que el filtro de elegibilidad y resguardo incluyan la actuación conjunta y representantes."""
        cr = nutrisa_folder.credit_risk
        filtro = cr.filtro_elegibilidad
        rep_filtro = next((item for item in filtro if "Representantes Legales" in item.get("parametro", "")), None)
        assert rep_filtro is not None
        assert "Actuación SII: En conjunto" in rep_filtro.get("detalle", "")
        assert "3 representante(s) registrado(s)" in rep_filtro.get("detalle", "")

        resguardo = cr.resguardo_comercial_sugerido
        assert "Forma de actuación registrada en SII: En conjunto" in resguardo or "Actuación SII: En conjunto" in resguardo
        assert "HECTOR GABRIEL RIOS LARRAIN" in resguardo
        assert "MARIA GLORIA RIOS LARRAIN" in resguardo
        assert "JOSE LUIS RODRIGUEZ CASANUEVA" in resguardo

    def test_generacion_pdf_nutrisa_layout(self, nutrisa_folder):
        """Genera el PDF y valida los textos clave de la versión v2.6."""
        pdf_bytes = PDFReport().generate(nutrisa_folder)
        assert len(pdf_bytes) > 10_000

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text_p1 = pdf.pages[0].extract_text()
            assert "(v2.6)" in text_p1
            assert "PERFIL TRIBUTARIO SÓLIDO" in text_p1
            assert "Inicial: M$ 7.200" in text_p1
            assert "Máxima: M$ 14.400" in text_p1
            assert "Actuación SII: En conjunto" in text_p1
            assert "Tope patrimonial no restrictivo en este RUT" in text_p1

            if len(pdf.pages) > 1:
                text_p2 = pdf.pages[1].extract_text()
                assert "Cód. 1657/628" in text_p2 or "Ingresos Giro" in text_p2
                assert "Cód. 1109/1690" in text_p2 or "RLI" in text_p2
                assert "Cód. 645" in text_p2 or "Capital Propio" in text_p2
                assert "Motor Determinista Cavilaria v2.6" in text_p2
