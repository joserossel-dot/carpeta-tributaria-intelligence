# Arquitectura — Carpeta Tributaria

## 1. Visión del proyecto

El objetivo no es extraer PDFs, sino construir un motor de inteligencia tributaria capaz de procesar distintos documentos del SII y generar un modelo de datos unificado.

## 2. Arquitectura

```
PDF
 → Extractor
 → Section Detector
 → Parsers
 → Normalizers
 → TaxFolder
 → Exporters
```

## 3. Principios

- Los parsers solo extraen datos.
- Los normalizers limpian y estandarizan.
- El TaxFolder es el contrato único de salida.
- Los exporters nunca modifican datos.
- Todo parser debe tener tests.
- No usar coordenadas fijas del PDF.
- Preferir regex y procesamiento semántico.
- Evitar duplicación de código.

## 4. Estructura del proyecto

| Carpeta       | Propósito                                      |
|---------------|-------------------------------------------------|
| `src/`        | Código fuente principal                         |
| `src/models/` | Modelos Pydantic (contrato de datos)            |
| `src/core/`   | Orquestación del pipeline de extracción         |
| `src/detectors/` | Detectores de secciones dentro del PDF       |
| `src/extractors/` | Extractores de texto desde PDFs             |
| `src/parsers/` | Parsers específicos por tipo de sección        |
| `src/normalizers/` | Normalizadores de datos extraídos          |
| `src/exporters/` | Exportadores a JSON, Excel, CSV, etc.        |
| `tests/`      | Tests unitarios y de integración                |
| `tests/fixtures/` | Snapshots y PDFs de prueba                  |
| `scripts/`    | Scripts utilitarios (parse, benchmark, validate) |
| `docs/`       | Documentación técnica                           |
| `examples/`   | PDFs de ejemplo del SII                         |

## 5. Convenciones

- Tipado con Pydantic.
- Tests obligatorios.
- Cobertura objetivo >90 %.
- Logging estructurado.
- Manejo uniforme de errores.
