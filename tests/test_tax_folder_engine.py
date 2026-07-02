from src.core.tax_folder_engine import TaxFolderEngine


class TestTaxFolderEngine:
    def test_parse_old_format(self) -> None:
        engine = TaxFolderEngine("examples/CPTAgrGonzagriLtda.pdf")
        result = engine.parse()

        assert result.contributor.rut == "79606270-3"
        assert result.contributor.razon_social == "AGRICOLA GONZAGRI LIMITADA"
        assert result.contributor.tipo_contribuyente == "Primera categoría"
        assert result.metadata.pages == 41
        assert result.metadata.source_file.endswith("CPTAgrGonzagriLtda.pdf")
        assert result.metadata.processing_time > 0
        assert len(result.f29) > 0
        assert result.f29[0].periodo == "2019-12"

    def test_parse_new_format(self) -> None:
        engine = TaxFolderEngine("examples/Carpeta Tributaria.CLINICA HYPERBARIC.pdf")
        result = engine.parse()

        assert result.contributor.rut == "77460385-9"
        assert result.contributor.razon_social == "CLINICA HYPERBARIC SPA"
        assert result.contributor.regimen_tributario is not None
        assert result.metadata.pages == 43
        assert result.metadata.processing_time > 0
        assert len(result.f29) > 0
        assert result.f29[0].periodo == "2026-04"

    def test_parse_model_dump(self) -> None:
        engine = TaxFolderEngine("examples/CPTExportadora.pdf")
        result = engine.parse()
        dumped = result.model_dump()

        assert dumped["contributor"]["rut"] == "99556090-9"
        assert dumped["metadata"]["pages"] == 41
        assert "source_file" in dumped["metadata"]
        assert "f29" in dumped
        assert len(dumped["f29"]) > 0
