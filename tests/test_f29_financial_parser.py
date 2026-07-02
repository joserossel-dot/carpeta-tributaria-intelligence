from decimal import Decimal

from src.models.f29 import F29, F29Detail
from src.models.monthly_tax import MonthlyTax
from src.parsers.f29_financial_parser import F29FinancialParser


class TestF29FinancialParser:
    def _make_f29(self, periodo: str, detalles: list[tuple[str, str, str]]) -> F29:
        return F29(
            periodo=periodo,
            folio="123",
            detalles=[F29Detail(codigo=c, glosa=g, valor=v) for c, g, v in detalles],
        )

    def test_parse_single_period(self) -> None:
        parser = F29FinancialParser()
        f29s = [
            self._make_f29("2024-01", [
                ("563", "BASE IMPONIBLE", "1000000"),
                ("538", "TOTAL DÉBITOS", "190000"),
                ("537", "TOTAL CRÉDITOS", "100000"),
                ("089", "IMP. DETERM. IVA", "90000"),
                ("062", "PPM NETO DET.", "25000"),
                ("511", "CRÉD. IVA POR DCTOS. ELECTRONICOS", "95000"),
            ]),
        ]
        result = parser.parse(f29s)
        assert len(result) == 1
        m = result[0]
        assert m.periodo == "2024-01"
        assert m.ventas_afectas == Decimal("1000000")
        assert m.debito_fiscal == Decimal("190000")
        assert m.credito_fiscal == Decimal("100000")
        assert m.iva_determinado == Decimal("90000")
        assert m.ppm == Decimal("25000")
        # compras = 95000 / 0.19 = 500000
        assert m.compras == Decimal("500000")
        # total_ventas = ventas_afectas only (exentas and exportacion are None)
        assert m.total_ventas == Decimal("1000000")

    def test_parse_multiple_periods_sorted(self) -> None:
        parser = F29FinancialParser()
        f29s = [
            self._make_f29("2024-02", [("563", "BASE IMPONIBLE", "2000000")]),
            self._make_f29("2024-01", [("563", "BASE IMPONIBLE", "1000000")]),
        ]
        result = parser.parse(f29s)
        assert len(result) == 2
        assert result[0].periodo == "2024-01"
        assert result[1].periodo == "2024-02"

    def test_parse_ventas_totales(self) -> None:
        parser = F29FinancialParser()
        f29s = [
            self._make_f29("2024-01", [
                ("563", "BASE IMPONIBLE", "1000000"),
                ("142", "VENTAS Y/O SERV. EXENTOS", "200000"),
                ("020", "EXPORTACIONES DEL MES", "300000"),
            ]),
        ]
        result = parser.parse(f29s)
        m = result[0]
        assert m.ventas_afectas == Decimal("1000000")
        assert m.ventas_exentas == Decimal("200000")
        assert m.ventas_exportacion == Decimal("300000")
        assert m.total_ventas == Decimal("1500000")

    def test_parse_missing_fields(self) -> None:
        parser = F29FinancialParser()
        f29s = [
            self._make_f29("2024-01", [
                ("563", "BASE IMPONIBLE", "500000"),
            ]),
        ]
        result = parser.parse(f29s)
        m = result[0]
        assert m.ventas_afectas == Decimal("500000")
        assert m.ventas_exentas is None
        assert m.ventas_exportacion is None
        assert m.total_ventas == Decimal("500000")
        assert m.compras is None
        assert m.debito_fiscal is None
        assert m.iva_determinado is None

    def test_parse_unknown_code_ignored(self) -> None:
        parser = F29FinancialParser()
        f29s = [
            self._make_f29("2024-01", [
                ("999", "CODIGO FANTASMA", "100000"),
            ]),
        ]
        result = parser.parse(f29s)
        m = result[0]
        assert m.ventas_afectas is None
        assert m.compras is None

    def test_parse_empty_f29(self) -> None:
        parser = F29FinancialParser()
        result = parser.parse([])
        assert result == []

    def test_compras_from_credit(self) -> None:
        parser = F29FinancialParser()
        f29s = [
            self._make_f29("2024-01", [
                ("511", "CRÉD. IVA POR DCTOS. ELECTRONICOS", "19000"),
            ]),
        ]
        result = parser.parse(f29s)
        m = result[0]
        # 19000 / 0.19 = 100000
        assert m.compras == Decimal("100000")

    def test_compras_zero_credit(self) -> None:
        parser = F29FinancialParser()
        f29s = [
            self._make_f29("2024-01", [
                ("511", "CRÉD. IVA POR DCTOS. ELECTRONICOS", "0"),
            ]),
        ]
        result = parser.parse(f29s)
        m = result[0]
        assert m.compras == Decimal("0")

    def test_multiple_credits_summed(self) -> None:
        parser = F29FinancialParser()
        f29s = [
            self._make_f29("2024-01", [
                ("511", "CRÉD. IVA POR DCTOS. ELECTRONICOS", "19000"),
                ("511", "CRÉD. IVA POR DCTOS. ELECTRÓNICOS", "38000"),
            ]),
        ]
        result = parser.parse(f29s)
        m = result[0]
        # (19000 + 38000) / 0.19 = 57000 / 0.19 = 300000
        assert m.compras == Decimal("300000")
