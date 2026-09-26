# INFORME FORENSE Y AUDITORÍA TÉCNICA QUANT: MOTOR DE CARPETA TRIBUTARIA Y RIESGO CREDITICIO B2B

**Autor:** Arquitecto de Software Senior & Auditor Cuantitativo de Riesgo Financiero  
**Fecha:** Septiembre 2026  
**Repositorio Evaluado:** `https://github.com/joserossel-dot/carpeta-tributaria-intelligence` (Branch: `carpeta-tributaria-score`)  
**Despliegue Auditado:** `https://carpeta-tributaria-score.onrender.com`  
**Destinatario:** Socio Director / Comité de Arquitectura y Crédito  

---

## RESUMEN EJECUTIVO PARA DIRECCIÓN

El proyecto actual constituye un **prototipo funcional de alta velocidad y arquitectura determinista** para la ingesta y extracción de datos de Carpetas Tributarias chilenas (PDF del SII), con un embrión de motor de decisión crediticia. 

### Fortalezas Clave
1. **Determinismo y Eficiencia:** Cero dependencia de LLMs para parsing; extracción basada en `pdfplumber` + regex compiladas en Python 3.12, con tiempos de respuesta sub-segundo (< 1s para PDFs de más de 40 páginas).
2. **Separación Conceptual Saludable (Hechos vs. Indicadores):** El módulo de riesgo (`src/credit/credit_risk_engine.py`) no castiga a ciegas conductas legales comunes de las PYMEs chilenas (como la postergación de IVA o el remanente estructural de IVA en empresas agrícolas/exportadoras).
3. **Modelado Tipado:** Estricta tipificación de datos mediante Pydantic v2 en modelos centrales.

### Brechas Críticas para un Comité de Crédito B2B 2.0
1. **Vulnerabilidad de Cálculo en F29:** El cálculo de compras mensuales no lee las compras netas reales (códigos 520, 524, 525, 562, 584) ni discrimina compras de activo fijo, sino que **infiere compras brutas dividiendo el Crédito Fiscal por Documentos Electrónicos (Cód. 511) por 0.19**. Si una empresa tiene notas de crédito, importaciones (Cód. 514/534), facturas de activo fijo (Cód. 525) o compras sin derecho a crédito fiscal (Cód. 562), la cifra queda distorsionada.
2. **Ceguera Tributaria en F22 (Regímenes Modernos):** El parser de F22 solo busca 7 códigos rígidos de Primera Categoría tradicional (Régimen 14A: Cód. 1657, 1694, 844, 36, 82, 1109, 305). **No soporta los regímenes ProPyme General (14 D3) ni ProPyme Transparente (14 D8)**, donde la base imponible y el Capital Propio Tributario Simplificado corren bajo códigos 1409, 1414, 1438, 1545 y 1702. En consecuencia, arroja campos no confiables ("No se encontró CPT") para la inmensa mayoría de las PYMEs en Chile.
3. **Ausencia de Asignación Automática de Cupo:** El sistema **no calcula de forma autónoma una Capacidad de Pago / Cupo Sugerido en CLP**. Únicamente recibe un `cupo_solicitado` arbitrario ingresado por el usuario y evalúa si el Capital Propio lo cubre \(N\) veces, o si la empresa tiene más de 70% de ventas facturadas para sugerir factoring por el mismo monto solicitado.
4. **Desconexión del Motor de Reglas en Producción:** `TaxFolderEngine` inicializa `RuleEngine` vacío sin registrar las reglas antes de llamar a `rule_engine.run(tax_folder)`. Por lo tanto, `tax_folder.validation` siempre viaja vacío y la pestaña de "Alertas" en la interfaz de Streamlit muestra sistemáticamente *"No existen alertas implementadas"*.
5. **Inexistencia de Auditoría de Continuidad Cronológica:** El sistema cuenta la cantidad de declaraciones presentes, pero no proyecta el calendario mensual real de 24 o 36 meses; no levanta alertas si faltan meses intermedios ("lagunas" u omisiones tributarias).

---

## PUNTO 1: ARQUITECTURA Y STACK TECNOLÓGICO

### 1.1. Árbol Completo de Archivos del Repositorio

```text
.
├── .gitignore
├── README.md
├── pyproject.toml
├── poetry.lock
├── app/
│   ├── README.md
│   ├── __init__.py
│   ├── main.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── activities.py
│   │   ├── alerts.py
│   │   ├── company_info.py
│   │   ├── corporate_info.py
│   │   ├── credit_score.py
│   │   ├── downloads.py
│   │   ├── export_data.py
│   │   ├── f22_summary.py
│   │   ├── kpi_cards.py
│   │   ├── monthly_chart.py
│   │   └── representatives.py
│   └── utils/
│       ├── __init__.py
│       ├── exporter.py
│       ├── formatting.py
│       └── pdf_processor.py
├── data/
│   └── sector_benchmarks.json
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ARQUITECTURA.md
│   ├── BACKLOG.md
│   ├── MODELO_DATOS.md
│   ├── ROADMAP.md
│   └── TAREAS.md
├── examples/
│   ├── 10.2023 BALANCE CLEVER LTDA.pdf
│   ├── 10.2023 BALANCE INVERSIONES PD.pdf
│   ├── 10.2023 BALANCE POWER PRO.pdf
│   ├── 10.2023 BALANCE RUTA RENTAL.pdf
│   ├── Balance 2022 Maquinas.pdf
│   ├── CPTAgrGonzagriLtda.pdf
│   ├── CPTAgrGonzalezLtda.pdf
│   ├── CPTExportadora.pdf
│   ├── CPTGonzagriS.A..pdf
│   ├── Carpeta Tributaria.CLINICA HYPERBARIC.pdf
│   └── Carpeta_Tributaria_Regular (4).pdf
├── scripts/
│   ├── analyze_examples.py
│   ├── benchmark.py
│   ├── discover_f29_codes.py
│   ├── generate_report.py
│   ├── parse_folder.py
│   ├── test_extractor.py
│   ├── validate_dataset.py
│   └── validate_extraction.py
├── src/
│   ├── __init__.py
│   ├── cli.py
│   ├── db_repository.py
│   ├── analyzers/
│   │   ├── __init__.py
│   │   ├── analysis_result.py
│   │   └── tax_analyzer.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py
│   ├── components/
│   │   └── f22_summary.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── orquestador.py
│   │   └── tax_folder_engine.py
│   ├── credit/
│   │   ├── __init__.py
│   │   ├── credit_risk_engine.py
│   │   └── sector_benchmark.py
│   ├── detectors/
│   │   ├── __init__.py
│   │   └── section_detector.py
│   ├── exporters/
│   │   ├── __init__.py
│   │   └── json_exporter.py
│   ├── extractors/
│   │   ├── __init__.py
│   │   └── pdf_extractor.py
│   ├── kpis/
│   │   ├── __init__.py
│   │   ├── kpi_engine.py
│   │   └── kpi_result.py
│   ├── mappers/
│   │   └── tax_folder_mapper.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── activity.py
│   │   ├── annual_tax_return.py
│   │   ├── company.py
│   │   ├── contributor.py
│   │   ├── corporate.py
│   │   ├── credit_risk.py
│   │   ├── extract_result.py
│   │   ├── f29.py
│   │   ├── monthly_tax.py
│   │   ├── section_result.py
│   │   └── tax_folder.py
│   ├── normalizers/
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── contributor_normalizer.py
│   │   └── f29_normalizer.py
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── contributor_parser.py
│   │   ├── corporate_parser.py
│   │   ├── economic_activities_parser.py
│   │   ├── f22_parser.py
│   │   ├── f29_financial_parser.py
│   │   └── f29_parser.py
│   ├── reports/
│   │   ├── __init__.py
│   │   └── executive_report.py
│   ├── rules/
│   │   ├── __init__.py
│   │   ├── base_rule.py
│   │   ├── rule_engine.py
│   │   ├── rule_result.py
│   │   ├── tax_rules.py
│   │   └── validation_result.py
│   └── services/
│       ├── __init__.py
│       └── monthly_tax_service.py
└── tests/
    ├── __init__.py
    ├── fixtures/
    │   ├── CPTAgrGonzalezLtda/expected.json
    │   ├── CPTExportadora/expected.json
    │   └── CPTGonzagri/expected.json
    ├── fixtures_validate/
    │   ├── CPTAgrGonzalezLtda.pdf
    │   ├── CPTExportadora.pdf
    │   ├── CPTGonzagriS.A..pdf
    │   └── corrupto.pdf
    ├── test_cli.py
    ├── test_contributor_normalizer.py
    ├── test_contributors_parser.py
    ├── test_credit_risk_engine.py
    ├── test_economic_activities_parser.py
    ├── test_executive_report.py
    ├── test_exporter.py
    ├── test_f22_parser.py
    ├── test_f22_parser_integration.py
    ├── test_f29_financial_parser.py
    ├── test_f29_financial_parser_integration.py
    ├── test_f29_normalizer.py
    ├── test_f29_parser.py
    ├── test_json_exporter.py
    ├── test_kpi_engine.py
    ├── test_monthly_tax_service.py
    ├── test_normalizers.py
    ├── test_rule_engine.py
    ├── test_section_detector.py
    ├── test_snapshots.py
    ├── test_tax_analyzer.py
    ├── test_tax_folder_engine.py
    ├── test_tax_folder_mapper.py
    ├── test_tax_rules.py
    └── test_validate_dataset.py
```

### 1.2. Lenguaje, Frameworks y Librerías

- **Lenguaje:** Python 3.12 (especificado en `pyproject.toml:11`).
- **Gestor de Dependencias:** Poetry (`poetry-core>=1.0.0`).
- **Framework Frontend / UI:** `Streamlit 1.58.0` (ejecutado en Render como proceso único web: `streamlit run app/main.py`).
- **Framework Backend / API:** Posee un esqueleto de `FastAPI 0.139.0` con `Uvicorn 0.49.0` en `src/api/main.py`, aunque la versión desplegada en Render opera directamente montando Streamlit contra el core en memoria.
- **Motor de Lectura de PDF:**
  - **Librería:** `pdfplumber ^0.11` (basado en `pdfminer.six`).
  - **Mecanismo:** Extracción de capas de texto nativo digital página por página (`page.extract_text()`).
  - **OCR:** **NO posee ningún motor de OCR** (ni Tesseract, ni AWS Textract, ni Google Document AI). Si el PDF es un escaneo rasterizado o imagen plana, `page.extract_text()` retorna cadena vacía y el sistema no procesa datos.
  - **Mapeo / Parsing:** 100% basado en expresiones regulares compiladas (`re.compile`) con heurísticas posicionales y cortes de sección.

### 1.3. ¿Utiliza LLMs / Inteligencia Artificial?

**NO utiliza ningún Modelo de Lenguaje (LLM), ni API de OpenAI, Anthropic, Gemini u Ollama.**
El sistema es **100% determinista, simbólico y algorítmico**. Su funcionamiento se basa en autómatas de estado finito modelados mediante expresiones regulares, normalización de strings, operaciones aritméticas con `decimal.Decimal` y reglas heurísticas condicionales `if-else`.

---

## PUNTO 2: MAPA EXACTO DE EXTRACCIÓN SII (F29, F22 Y PORTADA)

### 2.1. Identificación y Portada (`ContributorParser`, `CorporateParser`, `EconomicActivitiesParser`)

Ubicado en `src/parsers/contributor_parser.py`, `src/parsers/corporate_parser.py` y `src/parsers/economic_activities_parser.py`:

#### Campos extraídos de la Portada:
- **Razón Social:** Extraído con `Nombre del emisor:\s*(.+)`
- **RUT del Contribuyente:** Extraído con `RUT del emisor:\s*([\d.]+\s*[-−]\s*[\dkK])`
- **Fecha de Generación de Carpeta:** Extraído con `Fecha de generaci[oó]n de la carpeta:\s*([\d/]+(?:\s+[\d:]+)?)`
- **Fecha de Inicio de Actividades:** Extraído con `Fecha de Inicio de Actividades:\s*(.+)`
- **Tipo de Contribuyente (Categoría):** Extraído con `Categor[ií]a tributaria:\s*(.+)`
- **Régimen Tributario:** Extraído con `R[eé]gimen [Tt]ributario:\s*(.+)`
- **Domicilio Legal:** Multilínea con stop al iniciar sucursales o siguientes secciones (`Domicilio:\s*(.+)`).
- **Comuna:** Heurística basada en el último segmento separado por comas del domicilio.

#### Actividades Económicas (`EconomicActivitiesParser`):
- Extrae tabla con Código de 6 dígitos (`\d{6}`), Glosa descriptiva, Criterio de Principal/Secundaria (asume la primera fila como `principal=True`), y en formato nuevo: Categoría Tributaria y Fecha de Vigencia.

#### Estructura Societaria y Representación (`CorporateParser`):
- **Tipo de Sociedad:** `Sociedad\s+(?:del\s+)?[Tt]ipo:\s*(.+)`
- **Capital Social / Constitutivo:** `Capital\s*(?:[Ss]ocial|[Cc]onstitutivo)?:\s*\$?\s*([\d.]+)`
- **Fecha de Constitución:** `Fecha\s+de\s+[Cc]onstituci[oó]n:\s*(\d{2}[/\-]\d{2}[/\-]\d{4})`
- **Socios:** Nombre, RUT y Porcentaje de participación (`(\d{1,3}(?:[.,]\d{1,2})?)\s*%`).
- **Representantes Legales:** Nombre y RUT.

---

### 2.2. Formulario 29 (IVA): Códigos Capturados y Fragmento Real

El sistema realiza la captura en dos fases:
1. `F29Parser` (`src/parsers/f29_parser.py`): Extrae la tabla genérica `(Código, Glosa, Valor)` mediante la expresión regular de tuplas:
   ```python
   _RE_CODE_TUPLE: Pattern[str] = re.compile(
       r"(\d{3})\s+(.+?)\s+(-?[\d.,]+)(?=\s+\d{3}|$)"
   )
   ```
2. `F29FinancialParser` (`src/parsers/f29_financial_parser.py`): Mapea únicamente un subconjunto restringido de códigos a campos financieros directos.

#### Fragmento Textual del Mapeo de F29:
```python
# src/parsers/f29_financial_parser.py (líneas 8-20)
class F29FinancialParser:
    CODE_MAP: dict[str, str] = {
        "563": "ventas_afectas",
        "142": "ventas_exentas",
        "020": "ventas_exportacion",
        "538": "debito_fiscal",
        "537": "credito_fiscal",
        "089": "iva_determinado",
        "062": "ppm",
    }

    # código 511 = CRÉD. IVA POR DCTOS. ELECTRONICOS = 19% of purchases
    COMPRAS_CREDIT_CODE = "511"
    IVA_RATE = Decimal("0.19")
```

En adición, el motor de riesgo crediticio (`src/credit/credit_risk_engine.py`) busca de forma puntual 4 códigos adicionales dentro de los detalles del F29:
- **Cód. 502:** Débitos facturas emitidas (para calcular porcentaje facturado vs. boletas).
- **Cód. 111:** Débitos por boletas de ventas y servicios.
- **Cód. 779:** Postergación de pago de IVA (Ley Pro-Pyme).
- **Cód. 94:** Recargo por declaración fuera de plazo o pago con mora.
- **Cód. 504:** Remanente de crédito fiscal del mes anterior (usado únicamente como conteo de frecuencia).

#### Tabla Comparativa Forense de Códigos F29:

| Código SII | Glosa Oficial SII | ¿Capturado en el Proyecto? | ¿Cómo se usa? |
| :--- | :--- | :---: | :--- |
| **563** | Ventas / Servicios Facturados Afectos | **SÍ** | `ventas_afectas` en `MonthlyTax` |
| **142** | Ventas y/o Servicios Exentos o No Gravados | **SÍ** | `ventas_exentas` en `MonthlyTax` |
| **020** | Exportaciones | **SÍ** | `ventas_exportacion` en `MonthlyTax` |
| **538** | Total Débito Fiscal | **SÍ** | `debito_fiscal` en `MonthlyTax` |
| **537** | Total Crédito Fiscal | **SÍ** | `credito_fiscal` en `MonthlyTax` |
| **089** | Impuesto Determinado IVA | **SÍ** | `iva_determinado` en `MonthlyTax` |
| **062** | Pagos Provisionales Mensuales (PPM) | **SÍ** | `ppm` en `MonthlyTax` |
| **511** | Crédito IVA por Dctos. Electrónicos | **SÍ** | **Infiere compras:** `Cód. 511 / 0.19` |
| **502** | Débitos por Facturas Emitidas | **SÍ** | Proporción de facturación B2B en Score |
| **111** | Débitos por Boletas Emitidas | **SÍ** | Proporción de facturación B2C en Score |
| **779** | Postergación de Pago IVA | **SÍ** | Conteo de meses acogidos a postergación |
| **094** | Recargo por Mora / Intereses F29 | **SÍ** | Conteo de mora efectiva en Score |
| **504** | Remanente Crédito Mes Anterior | **SÍ (Parcial)** | Conteo de meses con saldo a favor (no se resta en margen) |
| **520** | Compras Internas Afectas Netas del Giro | **NO** | **Ignorado** (Cálculo usa 511 / 0.19) |
| **524** | Cantidad Facturas Activo Fijo Recibidas | **NO** | **Ignorado** |
| **525** | Crédito Fiscal Recuperable Activo Fijo | **NO** | **Ignorado** (Se mezcla en crédito fiscal global) |
| **528** | Crédito Fiscal por Importaciones | **NO** | **Ignorado** |
| **562** | Monto Neto Sin Derecho a Crédito Fiscal | **NO** | **Ignorado** |
| **584** | Compras Internas Exentas / No Gravadas | **NO** | **Ignorado** |
| **077** | Remanente Crédito Período Anterior Impugnado | **NO** | **Ignorado** |
| **048** | Devolución de Remanente (Art. 27 bis) | **NO** | **Ignorado** |
| **151** | Retención Cambio de Sujeto / Proveedores | **NO** | **Ignorado** |
| **755 / 756** | Retenciones de Terceros / Boletas Honorarios | **NO** | **Ignorado** |
| **091** | Total a Pagar en Moneda Nacional | **NO** | **Ignorado** |

---

### 2.3. Formulario 22 (Renta Anual): Códigos y Manejo de Regímenes

Ubicado en `src/parsers/f22_parser.py`:

```python
# src/parsers/f22_parser.py (líneas 31-39)
class F22Parser:
    _CODIGO_MAPPING = {
        "1657": "ingresos",
        "1694": "renta_liquida_imponible",
        "844": "capital_propio_tributario",
        "36": "ppm",
        "82": "creditos",
        "1109": "base_imponible",
        "305": "impuesto_determinado",
    }
```

#### Manejo de Regímenes Tributarios (14A, 14D3, 14D8)
- **Falla Estructural:** El código **NO realiza ninguna discriminación ni enrutamiento por régimen tributario**. Asume de manera estática que todos los contribuyentes declaran bajo el régimen semi-integrado general (14 A) en el Recuadro 12/13.
- **Impacto Financiero:** En Chile, más del 80% de las empresas comerciales y de servicios son PYMEs acogidas al régimen ProPyme General (Art. 14 D N° 3) o ProPyme Transparente (Art. 14 D N° 8):
  - En **14 D3**, la base imponible se declara en el **Cód. 1409 o 1414** (Recuadro 17) y el Capital Propio Tributario Simplificado se declara en el **Cód. 1545** (Recuadro 19).
  - En **14 D8**, el resultado tributario asignado se declara en el **Cód. 1438** (Recuadro 22) y el CPT Simplificado en el **Cód. 1545**.
  - Al buscar únicamente el Cód. 844 y 1694, **el sistema falla en extraer el CPT y la RLI de casi cualquier PYME**, disparando la advertencia de `CalidadDatos`: *"No se encontró Capital Propio Tributario"* y dejando sin calificar el indicador de Respaldo Estructural.

#### Manejo de Años Tributarios:
El parser agrupa las páginas identificando el patrón `AÑO TRIBUTARIO (\d{4})`. Agrupa páginas contiguas para soportar declaraciones de más de una plana, descarta páginas que pertenezcan a otras secciones (bienes raíces, vehículos) y ordena las declaraciones de manera descendente (año más reciente primero).

---

### 2.4. Control de Continuidad y Tratamiento de Meses

1. **Ordenamiento de Períodos:**
   - En `F29Parser._parse_page`, se parsea el período con `_RE_PERIODO_NUEVO` (`YYYYMM`) o `_RE_PERIODO_VIEJO` (`MM / YYYY`) normalizándolo a `YYYY-MM`.
   - Se ordenan de forma descendente en el parser (`reverse=True`) y luego de forma ascendente en `F29FinancialParser`.
2. **Detección de Meses No Declarados ("Huecos"):**
   - **NO está implementada.** En `CreditRiskEngine._evaluar_calidad_datos`:
     ```python
     return CalidadDatos(
         completitud_pct=completitud_pct,
         campos_no_confiables=campos_no_confiables,
         meses_f29_faltantes=[],  # <--- HARDCODED VACÍO
         veredicto=veredicto,
     )
     ```
   - Si la carpeta tributaria tiene los meses `2023-01`, `2023-02` y luego salta a `2023-08`, el sistema procesa 3 períodos como si fueran consecutivos; no construye una línea de tiempo continua para identificar omisiones de declaración.
3. **Declaraciones Sin Movimiento:**
   - Si la página del PDF contiene la frase `"No se registra declaración"` (`_RE_SIN_DECLARACION`), `_parse_page` retorna `None` y el mes es **ignorado y descartado**.
   - En `MonthlyTaxService`:
     ```python
     meses_sin = sum(
         1 for m in monthly_taxes
         if (m.total_ventas is None or m.total_ventas == 0)
     )
     ```
     Clasifica como "meses sin movimiento" cualquier período donde `total_ventas` sea 0 o nulo, ignorando si el mes tuvo compras operativas declaradas.

---

## PUNTO 3: AUDITORÍA DE LAS FÓRMULAS FINANCIERAS ACTUALES

### 3.1. Código Textual de Cálculo de Ventas y Compras

```python
# src/parsers/f29_financial_parser.py (líneas 36-77)
            for det in f29.detalles:
                campo = self.CODE_MAP.get(det.codigo)
                if not campo and det.codigo != self.COMPRAS_CREDIT_CODE:
                    continue
                valor = self._parse_valor(det.valor)
                if valor is None:
                    continue
                if det.codigo == self.COMPRAS_CREDIT_CODE:
                    # derive purchase amount from VAT credit ÷ 0.19
                    compras = self._credit_to_purchases(valor)
                    if compras is not None:
                        if row["compras"] is None:
                            row["compras"] = compras
                        else:
                            row["compras"] += compras
                elif campo:
                    if row[campo] is None:
                        row[campo] = valor
                    else:
                        row[campo] += valor

        result: list[MonthlyTax] = []
        for periodo in sorted(monthly.keys()):
            row = monthly[periodo]
            obs = observaciones[periodo]
            ventas_afectas = row["ventas_afectas"]
            ventas_exentas = row["ventas_exentas"]
            ventas_exportacion = row["ventas_exportacion"]
            total_ventas = self._sumar(ventas_afectas, ventas_exentas, ventas_exportacion)
            result.append(MonthlyTax(
                periodo=periodo,
                ventas_afectas=ventas_afectas,
                ventas_exentas=ventas_exentas,
                ventas_exportacion=ventas_exportacion,
                compras=row["compras"],
                debito_fiscal=row["debito_fiscal"],
                credito_fiscal=row["credito_fiscal"],
                iva_determinado=row["iva_determinado"],
                ppm=row["ppm"],
                total_ventas=total_ventas,
                observaciones=obs,
            ))
```

```python
# src/parsers/f29_financial_parser.py (líneas 90-101)
    @staticmethod
    def _credit_to_purchases(credit: Decimal) -> Decimal | None:
        if credit == 0:
            return Decimal("0")
        return (credit / F29FinancialParser.IVA_RATE).quantize(Decimal("0"))

    @staticmethod
    def _sumar(*args: Decimal | None) -> Decimal | None:
        vals = [v for v in args if v is not None]
        if not vals:
            return None
        return sum(vals, Decimal("0"))
```

### 3.2. Evaluación Crítica de Fórmulas de Ventas, Compras y Margen

#### A. Ventas Mensuales:
$$\text{Total Ventas} = \text{Cód. 563 (Afectas)} + \text{Cód. 142 (Exentas)} + \text{Cód. 020 (Exportaciones)}$$
- **Dictamen:** **Correcto**. Suma las ventas netas de los tres regímenes operativos de facturación. Si un mes no tiene ventas exentas ni exportación, toma el neto afecto del código 563.

#### B. Compras Mensuales:
$$\text{Compras Calculadas} = \frac{\text{Cód. 511}}{\text{0.19}}$$
- **Dictamen:** **CRÍTICAMENTE DEFICIENTE**.
  1. Utiliza el **Crédito IVA por Documentos Electrónicos (Cód. 511)** y lo divide por `0.19`.
  2. **No extrae los Códigos Netos Reales:** El SII entrega directamente los valores netos de compra:
     - **Cód. 520:** Compras internas afectas netas del giro.
     - **Cód. 524 / 525:** Inversiones en Activo Fijo (deben aislarse del gasto operacional / COGS corriente).
     - **Cód. 562:** Compras sin derecho a crédito fiscal (ej. combustibles, supermercado con restricción, proveedores exentos).
     - **Cód. 584:** Compras internas exentas o no gravadas.
  3. **Notas de Crédito y Débito:** Si existen notas de crédito recibidas (Cód. 527/528) o rectificaciones, no se netean adecuadamente sobre el flujo físico de abastecimiento.

#### C. Margen Operativo / Bruto:
En `CreditRiskEngine._margen_vs_giro`:
```python
# src/credit/credit_risk_engine.py (líneas 200-205)
        last_12 = tax_folder.monthly_taxes[-12:] if len(tax_folder.monthly_taxes) >= 12 else tax_folder.monthly_taxes
        debitos = [m.debito_fiscal for m in last_12 if m.debito_fiscal is not None]
        creditos = [m.credito_fiscal for m in last_12 if m.credito_fiscal is not None]

        ratio = None
        if debitos and creditos and sum(creditos) > 0:
            ratio = round(float(sum(debitos) / sum(creditos)), 3)
```
- **Dictamen:**
  1. Utiliza como proxy de margen el ratio:
     $$\text{Ratio Débito/Crédito 12M} = \frac{\sum_{12} \text{Cód. 538 (Total Débitos)}}{\sum_{12} \text{Cód. 537 (Total Créditos)}}$$
  2. **No resta el Remanente de Crédito Fiscal del mes anterior (Cód. 504):** El código 537 incluye por normativa del SII: `Crédito del mes + Remanente Cód. 504 + Ajustes`. Si una empresa arrastra un remanente histórico abultado de IVA de años previos, el Cód. 537 se infla artificialmente cada mes, colapsando el ratio $\frac{\text{Débito}}{\text{Crédito}}$ y haciendo que el motor crea falsamente que la empresa opera a pérdida o sin margen.

### 3.3. Ratios Financieros Calculados vs. Omitidos

| Ratio Financiero | ¿Calculado Actualmente? | Ubicación / Fórmula |
| :--- | :---: | :--- |
| **Crecimiento Ventas Semestral** | **SÍ** | `MonthlyTaxService._calc_crecimiento`: $\frac{\text{Ventas 2do Semestre} - \text{Ventas 1er Semestre}}{\text{Ventas 1er Semestre}} \times 100$ |
| **Volatilidad / Meses Sin Movimiento** | **SÍ** | `MonthlyTaxService`: Conteo de meses con ventas $= 0$ o nulas |
| **Ratio Débito / Crédito 12M** | **SÍ** | `CreditRiskEngine._margen_vs_giro`: $\frac{\sum \text{Débito Fiscal}}{\sum \text{Crédito Fiscal}}$ |
| **Razón Corriente (Liquidez)** | **NO** | No disponible en Carpeta Tributaria estándar |
| **Prueba Ácida** | **NO** | No disponible en Carpeta Tributaria estándar |
| **Endeudamiento Bancario (CMF)** | **NO** | No extraído (requeriría deuda financiera CMF) |
| **Cobertura de Intereses (EBITDA / Intereses)** | **NO** | No implementado |
| **Apalancamiento Tributario (Pasivos / CPT)** | **NO** | No implementado (F22 posee Pasivo Exigible Cód. 102/103/523 en balances) |

---

## PUNTO 4: LÓGICA DEL "SCORE" Y REGLAS DE DECISIÓN

### 4.1. Código Textual Completo del Motor de Scoring

```python
# src/credit/credit_risk_engine.py (líneas 37-59, 162-281)
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
```

```python
# src/credit/credit_risk_engine.py: Reglas de los 3 Indicadores
    # 1. Mora Efectiva (Cód. 94)
    pct_mora = meses_con_recargo / n
    score_mora = round(max(0, 100 - pct_mora * 100 * 4))  # Cada mes de mora castiga 4x

    # 2. Margen vs. Giro (Ratio Débito/Crédito vs. Benchmark)
    relativo = ratio / ratio_promedio
    score_margen = round(min(100, max(0, relativo * 70)))

    # 3. Respaldo Estructural (CPT vs. Cupo Solicitado)
    veces = round(cpt / cupo_solicitado, 2)
    score_cpt = round(min(100, max(0, veces * 25)))  # Requiere 4x cobertura para llegar a 100 pts
```

```python
# src/credit/credit_risk_engine.py: Composición y Ponderadores
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
            return None
        return round(sum(scores) / len(scores))
```

### 4.2. Ponderación de Variables y Umbrales

1. **Gate Previo (Calidad de Datos):**
   - Requiere obligatoriamente: Razón social presente y al menos 6 meses de F29. Si no cumple, el veredicto es `DATOS_INSUFICIENTES` y **no se calcula score**.
2. **Ponderaciones del Score Compuesto:**
   - El sistema **NO aplica una matriz de ponderaciones fijas (ej. 40% mora, 40% margen, 20% CPT)**.
   - Aplica un **promedio simple no ponderado** entre los indicadores que tengan puntaje no nulo (`sum(scores) / len(scores)`).
   - Si menos de 2 indicadores tienen puntaje válido, el Score Compuesto es `None` (`NO_EVALUABLE`).
   - Dado que el benchmark sectorial (`data/sector_benchmarks.json`) está actualmente vacío (`{}`), el indicador `margen_vs_giro` siempre tiene `score = None`. En la práctica comercial actual, para que haya score, el usuario **está forzado a ingresar un cupo solicitado** para que `respaldo_estructural` puntúe junto a `mora_efectiva`.
3. **Umbrales de Decisión Crediticia:**
   - **Score $\ge 70$:** `APROBADO`
   - **$50 \le \text{Score} < 70$:** `APROBADO_CON_CONDICIONES`
   - **Score $< 50$:** `RECHAZADO`
   - **Score $= \text{None}$:** `NO_EVALUABLE`

### 4.3. Alertas y Banderas Rojas Actuales

El motor de crédito (`CreditRiskEngine._alertas_y_fortalezas`) levanta las siguientes banderas:
- **Alerta de Mora:** `{N} mes(es) con recargo/interés por mora efectiva en el período evaluado` (si Cód. 94 > 0).
- **Alerta de Benchmark:** `Margen vs. giro sin benchmark confiable todavía (muestra actual: {N} empresas del rubro)`.
- **Alerta de Infracobertura Patrimonial:** `Capital propio tributario por debajo del cupo solicitado` (si CPT / Cupo < 1.0x).
- **Fortalezas:**
  - `Cero meses con mora efectiva en {N} meses de historia evaluados`.
  - `Capital propio tributario cubre {N}x el cupo solicitado` (si cobertura $\ge 3.0$x).

### 4.4. ¿Calcula Monto de Línea de Crédito / Cupo Sugerido ($)?

**NO calcula ningún cupo sugerido de forma autónoma.**
- El sistema no analiza el flujo de caja, ni el capital de trabajo operativo (días de cobro vs. días de pago), ni un porcentaje de las ventas mensuales (ej. 30 o 60 días de facturación promedio).
- La única mención a un cupo sugerido se encuentra en los **Caminos de Mitigación** (`CaminoMitigacion`), donde si el porcentaje facturado es superior al 70%, asigna:
  ```python
  cupo_sugerido = cupo_solicitado if alto_facturado else None
  ```
  Es decir: **se limita a reflejar exactamente el mismo monto que el usuario digitó manualmente en la pantalla.**

---

## PUNTO 5: ESQUEMA DE DATOS (OUTPUT JSON / MODELOS INTERNOS)

El objeto devuelto por `TaxFolderEngine.parse()` es una instancia serializable del modelo Pydantic `TaxFolder` (`src/models/tax_folder.py`), cuya estructura canónica JSON es la siguiente:

```json
{
  "contributor": {
    "rut": "str | null",
    "razon_social": "str | null",
    "fecha_generacion": "str | null",
    "fecha_inicio_actividades": "str | null",
    "domicilio": "str | null",
    "comuna": "str | null",
    "region": "str | null",
    "tipo_contribuyente": "str | null",
    "regimen_tributario": "str | null"
  },
  "representatives": [
    {
      "rut": "str",
      "nombre": "str",
      "cargo": "str | null"
    }
  ],
  "activities": [
    {
      "codigo": "str",
      "descripcion": "str",
      "principal": "bool",
      "categoria": "str | null",
      "fecha_inicio": "str | null"
    }
  ],
  "corporate": {
    "tipo_sociedad": "str | null",
    "fecha_constitucion": "str | null",
    "capital": "str | null",
    "socios": [
      {
        "rut": "str",
        "nombre": "str",
        "participacion": "str | null"
      }
    ],
    "representantes": [
      {
        "rut": "str",
        "nombre": "str",
        "cargo": "str | null"
      }
    ]
  },
  "f29": [
    {
      "periodo": "str (YYYY-MM)",
      "folio": "str",
      "fecha_presentacion": "str | null",
      "detalles": [
        {
          "codigo": "str",
          "glosa": "str",
          "valor": "str"
        }
      ]
    }
  ],
  "monthly_taxes": [
    {
      "periodo": "str (YYYY-MM)",
      "ventas_afectas": "Decimal | null",
      "ventas_exentas": "Decimal | null",
      "ventas_exportacion": "Decimal | null",
      "compras": "Decimal | null",
      "debito_fiscal": "Decimal | null",
      "credito_fiscal": "Decimal | null",
      "iva_determinado": "Decimal | null",
      "ppm": "Decimal | null",
      "total_ventas": "Decimal | null",
      "observaciones": ["str"]
    }
  ],
  "monthly_analysis": {
    "total_months": "int",
    "ventas_ultimos_12": "Decimal | null",
    "compras_ultimos_12": "Decimal | null",
    "promedio_ventas_mensual": "Decimal | null",
    "promedio_compras_mensual": "Decimal | null",
    "crecimiento_anual": "Decimal | null",
    "meses_sin_movimiento": "int",
    "mejor_mes": "str | null",
    "peor_mes": "str | null"
  },
  "f22": [
    {
      "anio_tributario": "str",
      "ingresos": "int | null",
      "renta_liquida_imponible": "int | null",
      "capital_propio_tributario": "int | null",
      "impuesto_determinado": "int | null",
      "ppm": "int | null",
      "creditos": "int | null",
      "perdidas": "int | null",
      "base_imponible": "int | null",
      "resultado_tributario": "int | null",
      "observaciones": ["str"]
    }
  ],
  "credit_risk": {
    "calidad_datos": {
      "completitud_pct": "float | null",
      "campos_no_confiables": [
        {
          "campo": "str",
          "motivo": "str"
        }
      ],
      "meses_f29_faltantes": ["str"],
      "veredicto": "str ('APTO_PARA_SCORING' | 'DATOS_INSUFICIENTES')"
    },
    "hechos": {
      "composicion_ventas": {
        "pct_facturado": "float | null",
        "pct_boletas": "float | null",
        "monto_facturado_estimado": "int | null",
        "meses_evaluados": "int",
        "nota": "str | null"
      },
      "postergaciones_iva": {
        "meses_con_postergacion": "int",
        "total_meses_evaluados": "int",
        "periodos": ["str"]
      }
    },
    "indicadores": {
      "mora_efectiva": {
        "score": "int | null (0-100)",
        "meses_con_recargo": "int",
        "meses_con_remanente_credito": "int",
        "meses_evaluados": "int",
        "confianza": "str",
        "criterio": "str"
      },
      "margen_vs_giro": {
        "score": "int | null (0-100)",
        "ratio_debito_credito_12m": "float | null",
        "codigo_actividad": "str | null",
        "descripcion_actividad": "str | null",
        "ratio_promedio_sector": "float | null",
        "n_empresas_referencia": "int",
        "confianza": "str",
        "criterio": "str"
      },
      "respaldo_estructural": {
        "score": "int | null (0-100)",
        "capital_propio_tributario": "int | null",
        "cupo_solicitado": "int | null",
        "veces_cobertura": "float | null",
        "confianza": "str",
        "criterio": "str"
      }
    },
    "score_compuesto": "int | null (0-100)",
    "decision": {
      "resultado_base": "str ('APROBADO' | 'APROBADO_CON_CONDICIONES' | 'RECHAZADO' | 'NO_EVALUABLE')",
      "producto_evaluado": "str",
      "caminos_mitigacion": [
        {
          "condicion": "str",
          "aplica": "bool",
          "resultado": "str",
          "cupo_sugerido": "int | null",
          "justificacion": "str"
        }
      ]
    },
    "alertas": ["str"],
    "fortalezas": ["str"]
  },
  "validation": [
    {
      "code": "str",
      "severity": "str",
      "title": "str",
      "description": "str",
      "recommendation": "str | null"
    }
  ],
  "kpis": {
    "company_age_years": "float | null",
    "activity_count": "int",
    "principal_activity": "str | null",
    "representative_count": "int",
    "property_count": "int",
    "vehicle_count": "int",
    "f29_count": "int",
    "first_f29_period": "str | null",
    "last_f29_period": "str | null",
    "declared_months": "int | null",
    "processing_timestamp": "str (ISO)"
  },
  "metadata": {
    "source_file": "str",
    "pages": "int",
    "processing_time": "float"
  }
}
```

---

## PUNTO 6: ESTADO DEL FRONTEND Y FLUJO DE USUARIO EN RENDER

Despliegue verificado: `https://carpeta-tributaria-score.onrender.com`

### 6.1. Inputs Solicitados al Usuario
En la pantalla inicial de Streamlit (`app/main.py`):
1. **Selector / Drag & Drop de Archivo:**
   - Etiqueta: *"Arrastra un PDF aquí"*.
   - Acepta exclusivamente archivos `.pdf` individuales.
2. **Input Numérico:**
   - Etiqueta: *"Cupo de crédito solicitado (CLP, opcional)"*.
   - Tipo: Numérico entero con pasos de $\$1.000.000$, valor por defecto $0$.
3. **Botón de Acción:**
   - Botón *"Analizar"* (tipo primario).

### 6.2. Visualización de Resultados en Producción

Una vez procesado el archivo, la pantalla despliega de arriba hacia abajo:

1. **Header de Estado:** Tiempo de procesamiento y cantidad de páginas procesadas (ej. `Procesado en 0.45s (36 páginas)`).
2. **KPI Cards Superiores (5 Columnas):**
   - Ventas últimos 12 meses (formato moneda CLP).
   - Compras últimos 12 meses (formato moneda CLP).
   - Promedio ventas mensual (CLP).
   - Promedio compras mensual (CLP).
   - Cantidad de F29 procesados (unidades).
3. **Estructura de 7 Pestañas (`st.tabs`):**
   - **Tab 1 ("Empresa"):**
     - Subsección Datos Empresa: Razón social, RUT, Giro principal, Régimen tributario, Inicio de actividades.
     - Subsección Actividades Económicas: Tabla con Código, Descripción, si es Principal, Categoría y Fecha inicio.
     - Subsección Representantes Legales: Tabla con RUT y Nombre.
   - **Tab 2 ("Socios y Administración"):**
     - Métricas de Tipo de Sociedad, Fecha de Constitución y Capital Constitutivo.
     - Tabla interactiva de Socios (RUT, Nombre, Participación %).
     - Tabla de Representantes Legales.
   - **Tab 3 ("IVA Mensual"):**
     - Gráfico de líneas temporal (`st.line_chart`): Serie cronológica comparativa de Ventas vs. Compras.
     - Tabla detallada mes a mes con los montos formateados.
   - **Tab 4 ("F22"):**
     - Tabla histórica comparativa de declaraciones anuales: Columnas de Año tributario, Ingresos, RLI, CPT, Impuesto Determinado, PPM, Créditos, Pérdidas, Base Imponible y Resultado Tributario.
   - **Tab 5 ("Score Crediticio"):**
     - Banner de Calidad de Datos (`APTO_PARA_SCORING` / `DATOS_INSUFICIENTES` y % de completitud).
     - Acordeón de campos no confiables detectados.
     - Métrica de Score Compuesto (`XX/100` o `No evaluable`) y Badge coloreado de Decisión (`APROBADO` en verde, `APROBADO_CON_CONDICIONES` en naranja, `RECHAZADO` en rojo).
     - Bloque de Hechos: % Facturado vs. % Boleta y Frecuencia de Postergaciones de IVA.
     - Bloque de Indicadores: Score y confianza de Mora Efectiva, Margen vs. Giro y Respaldo Estructural.
     - Acordeones desplegables de Caminos de Mitigación (Cesión de facturas / Pago contado con descuento).
     - Listas con viñetas de Fortalezas detectadas y Alertas.
   - **Tab 6 ("Alertas"):**
     - Actualmente muestra siempre *"No existen alertas implementadas"* debido a que `rule_engine` no tiene reglas registradas en el flujo principal del motor.
   - **Tab 7 ("Exportación"):**
     - Filtro selector de rango de períodos (`Fecha desde` a `Fecha hasta`).
     - Selector de formato (Excel `.xlsx` o CSV).
     - Botón de descarga de la data de ventas y compras procesada.
4. **Sección Inferior de Descargas:**
   - Botón *"Descargar JSON"* (`carpeta_tributaria.json`).
   - Botón *"Descargar Reporte Markdown"* (`reporte.md`).

---

## CONCLUSIÓN FORENSE Y MATRIZ DE RIESGO PARA LA VERSIÓN 2.0

| Dimensión | Estado Actual (v1.0) | Severidad | Requerimiento Crítico para Motor 2.0 |
| :--- | :--- | :---: | :--- |
| **Parsing F29** | Infiere compras dividiendo Cód. 511 por 0.19; ignora compras netas directas y activo fijo. | **CRÍTICA** | Mapear Códigos 520, 524, 525, 562, 584, 504, 537 y 091. Aislar compras corrientes de capex de activo fijo. |
| **Parsing F22** | Rígido para Régimen 14A. No reconoce ProPyme General (14 D3) ni Transparente (14 D8). | **CRÍTICA** | Incorporar Recuadros 17 a 22 del F22 (Códigos 1409, 1414, 1438, 1545, 1702) para cálculo real de CPT y base imponible en PYMEs. |
| **Cálculo de Margen** | Ratio Débito/Crédito contaminado con Remanente de IVA anterior (Cód. 504). | **ALTA** | Restar Cód. 504 del Crédito Fiscal antes de computar el ratio operacional de valor agregado. |
| **Asignación de Cupo** | 100% pasivo. Depende del cupo digitado por el usuario; no calcula capacidad de pago en CLP. | **CRÍTICA** | Implementar algoritmo cuantitativo de cupo: Máximo entre % de Facturación B2B ponderada, Capacidad de Servicio de Deuda (EBITDA proxy) y Cobertura Patrimonial. |
| **Continuidad Temporal** | No detecta saltos o meses omitidos entre el primer y último F29. | **MEDIA** | Crear una grilla temporal estricta de 24/36 meses y marcar banderas de "Omisión Tributaria / Mes No Declarado". |
| **Alertas en UI** | Desconectadas por bug de inicialización en `TaxFolderEngine`. | **BAJA** | Registrar reglas en `RuleEngine` o unificar con el módulo `analysis` y `credit_risk.alertas`. |
