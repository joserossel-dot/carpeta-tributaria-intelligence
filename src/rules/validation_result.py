from enum import Enum

from pydantic import BaseModel


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationResult(BaseModel):
    severity: Severity
    code: str
    title: str
    description: str
    recommendation: str
