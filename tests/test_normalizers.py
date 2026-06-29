from src.normalizers.common import (
    normalize_date,
    normalize_money,
    normalize_period,
    normalize_rut,
    normalize_text,
)


class TestNormalizeRut:
    def test_with_dots(self) -> None:
        assert normalize_rut("79.606.270-3") == "79606270-3"

    def test_without_dots(self) -> None:
        assert normalize_rut("79606270-3") == "79606270-3"

    def test_with_spaces(self) -> None:
        assert normalize_rut("77442850 - K") == "77442850-K"

    def test_with_long_dash(self) -> None:
        assert normalize_rut("99556090 − 9") == "99556090-9"

    def test_lowercase_dv(self) -> None:
        assert normalize_rut("78155540-1") == "78155540-1"

    def test_k_dv(self) -> None:
        assert normalize_rut("77442850-k") == "77442850-K"

    def test_returns_original_if_invalid(self) -> None:
        assert normalize_rut("invalido") == "invalido"


class TestNormalizeDate:
    def test_dd_mm_yyyy(self) -> None:
        assert normalize_date("30/01/2020") == "2020-01-30"

    def test_dd_mm_yyyy_dash(self) -> None:
        assert normalize_date("05-06-2000") == "2000-06-05"

    def test_single_digits(self) -> None:
        assert normalize_date("01/02/2020") == "2020-02-01"

    def test_returns_none_for_invalid(self) -> None:
        assert normalize_date("Anterior a 1993") is None

    def test_returns_none_for_empty(self) -> None:
        assert normalize_date("") is None


class TestNormalizePeriod:
    def test_already_normalized(self) -> None:
        assert normalize_period("2020-01") == "2020-01"

    def test_compact_yyyymm(self) -> None:
        assert normalize_period("202604") == "2026-04"

    def test_old_format_mm_yyyy(self) -> None:
        assert normalize_period("12 / 2019") == "2019-12"

    def test_old_format_no_spaces(self) -> None:
        assert normalize_period("12/2019") == "2019-12"

    def test_single_digit_month(self) -> None:
        assert normalize_period("3/2020") == "2020-03"

    def test_returns_none_for_invalid(self) -> None:
        assert normalize_period("") is None


class TestNormalizeMoney:
    def test_integer_with_dots(self) -> None:
        assert normalize_money("236.141.139") == "236141139"

    def test_small_integer(self) -> None:
        assert normalize_money("26") == "26"

    def test_decimal_with_comma(self) -> None:
        assert normalize_money("1,60") == "1.60"

    def test_decimal_with_comma_and_dots(self) -> None:
        assert normalize_money("1.234,56") == "1234.56"

    def test_zero(self) -> None:
        assert normalize_money("0") == "0"

    def test_negative(self) -> None:
        assert normalize_money("-100") == "-100"

    def test_returns_original_if_not_money(self) -> None:
        assert normalize_money("N/A") == "N/A"


class TestNormalizeText:
    def test_strips_whitespace(self) -> None:
        assert normalize_text("  HOLA  ") == "HOLA"

    def test_collapses_multiple_spaces(self) -> None:
        assert normalize_text("AGRICOLA  GONZAGRI  LIMITADA") == "AGRICOLA GONZAGRI LIMITADA"

    def test_collapses_newlines(self) -> None:
        assert normalize_text("FUNDO SANTA MARTA S/N\nMOLINA") == "FUNDO SANTA MARTA S/N MOLINA"

    def test_strips_and_collapses(self) -> None:
        assert normalize_text("  texto   con  espacios  ") == "texto con espacios"

    def test_empty_string(self) -> None:
        assert normalize_text("") == ""

    def test_single_word(self) -> None:
        assert normalize_text("  SOLO  ") == "SOLO"
