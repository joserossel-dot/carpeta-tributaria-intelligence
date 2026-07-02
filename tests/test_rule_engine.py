from src.models.tax_folder import Metadata, TaxFolder
from src.rules.base_rule import BaseRule
from src.rules.rule_engine import RuleEngine
from src.rules.validation_result import Severity, ValidationResult


class _PassRule(BaseRule):
    def check(self, tax_folder: TaxFolder) -> ValidationResult | None:
        return None


class _FailRule(BaseRule):
    def check(self, tax_folder: TaxFolder) -> ValidationResult | None:
        return ValidationResult(
            severity=Severity.ERROR,
            code="TEST-001",
            title="Test Error",
            description="Something is wrong",
            recommendation="Fix it",
        )


class _AnotherRule(BaseRule):
    def check(self, tax_folder: TaxFolder) -> ValidationResult | None:
        return ValidationResult(
            severity=Severity.WARNING,
            code="TEST-002",
            title="Test Warning",
            description="Be careful",
            recommendation="Check it",
        )


class TestRuleEngine:
    def test_empty_engine_returns_empty_list(self) -> None:
        engine = RuleEngine()
        tf = TaxFolder(
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        assert engine.run(tf) == []

    def test_single_rule_returns_result(self) -> None:
        engine = RuleEngine()
        engine.register(_FailRule())
        tf = TaxFolder(
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        results = engine.run(tf)
        assert len(results) == 1
        assert results[0].code == "TEST-001"
        assert results[0].severity == Severity.ERROR

    def test_pass_rule_excluded(self) -> None:
        engine = RuleEngine()
        engine.register(_PassRule())
        engine.register(_FailRule())
        tf = TaxFolder(
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        results = engine.run(tf)
        assert len(results) == 1
        assert results[0].code == "TEST-001"

    def test_multiple_rules(self) -> None:
        engine = RuleEngine()
        engine.register(_FailRule())
        engine.register(_AnotherRule())
        tf = TaxFolder(
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        results = engine.run(tf)
        assert len(results) == 2
        assert results[0].code == "TEST-001"
        assert results[1].code == "TEST-002"

    def test_severity_enum_values(self) -> None:
        assert Severity.INFO.value == "info"
        assert Severity.WARNING.value == "warning"
        assert Severity.ERROR.value == "error"
        assert Severity.CRITICAL.value == "critical"

    def test_validation_result_fields(self) -> None:
        r = ValidationResult(
            severity=Severity.CRITICAL,
            code="CRIT-001",
            title="Critical error",
            description="Something catastrophic",
            recommendation="Stop everything",
        )
        assert r.severity == Severity.CRITICAL
        assert r.code == "CRIT-001"
        assert r.title == "Critical error"
        assert r.description == "Something catastrophic"
        assert r.recommendation == "Stop everything"


class TestTaxFolderValidation:
    def test_tax_folder_has_validation_field(self) -> None:
        tf = TaxFolder(
            metadata=Metadata(source_file="test.pdf", pages=1, processing_time=0.0),
        )
        assert hasattr(tf, "validation")
        assert tf.validation == []

    def test_engine_populates_empty_validation(self) -> None:
        from src.core.tax_folder_engine import TaxFolderEngine

        engine = TaxFolderEngine("examples/CPTExportadora.pdf")
        result = engine.parse()
        assert hasattr(result, "validation")
        assert result.validation == []

    def test_validation_in_model_dump(self) -> None:
        from src.core.tax_folder_engine import TaxFolderEngine

        engine = TaxFolderEngine("examples/CPTExportadora.pdf")
        result = engine.parse()
        dumped = result.model_dump()
        assert "validation" in dumped
        assert dumped["validation"] == []
