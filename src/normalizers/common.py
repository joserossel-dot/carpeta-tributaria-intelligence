import re
from typing import Pattern

_RUT_PATTERN: Pattern[str] = re.compile(
    r"^(\d{1,3}(?:\.?\d{3})*)\s*[-−]\s*([\dkK])$"
)
_DATE_PATTERN: Pattern[str] = re.compile(r"^(\d{2})[/\-](\d{2})[/\-](\d{4})$")
_PERIOD_PATTERN: Pattern[str] = re.compile(r"^(\d{4})-(\d{2})$")
_MONEY_PATTERN: Pattern[str] = re.compile(r"^-?[\d.,]+$")


def normalize_rut(rut: str) -> str:
    m = _RUT_PATTERN.match(rut.strip())
    if not m:
        return rut.strip()
    num = m.group(1).replace(".", "")
    dv = m.group(2).upper()
    return f"{num}-{dv}"


def normalize_date(date_str: str) -> str | None:
    m = _DATE_PATTERN.match(date_str.strip())
    if not m:
        return None
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"


def normalize_period(period: str) -> str | None:
    clean = period.strip().replace(" ", "")
    m = _PERIOD_PATTERN.match(clean)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.match(r"^(\d{4})(\d{2})$", clean)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.match(r"^(\d{1,2})\s*/\s*(\d{4})$", clean)
    if m:
        return f"{m.group(2)}-{int(m.group(1)):02d}"
    return None


def normalize_money(value: str) -> str:
    clean = value.strip()
    if not _MONEY_PATTERN.match(clean):
        return clean
    if "," in clean:
        clean = clean.replace(".", "")
        clean = clean.replace(",", ".")
        parts = clean.split(".")
        if len(parts) == 2:
            clean = f"{parts[0]}.{parts[1]}"
        return clean
    clean = clean.replace(".", "")
    return clean


def normalize_text(text: str) -> str:
    return " ".join(text.strip().split())
