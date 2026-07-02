from pydantic import BaseModel


class AnalysisResult(BaseModel):
    alerts: list = []
    warnings: list = []
    statistics: dict = {}
    metrics: dict = {}
