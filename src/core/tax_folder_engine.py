import time
from pathlib import Path

from src.analyzers.tax_analyzer import TaxAnalyzer
from src.detectors.section_detector import SectionDetector
from src.extractors.pdf_extractor import PDFExtractor
from src.kpis.kpi_engine import KPIEngine
from src.mappers.tax_folder_mapper import TaxFolderMapper
from src.models.tax_folder import Metadata, TaxFolder
from src.parsers.contributor_parser import ContributorParser
from src.parsers.corporate_parser import CorporateParser
from src.parsers.economic_activities_parser import EconomicActivitiesParser
from src.parsers.f22_parser import F22Parser
from src.parsers.f29_financial_parser import F29FinancialParser
from src.parsers.f29_parser import F29Parser
from src.rules.rule_engine import RuleEngine
from src.services.monthly_tax_service import MonthlyTaxService


class TaxFolderEngine:
    VERSION = "0.1.0"

    def __init__(self, pdf_path: str) -> None:
        self.pdf_path = pdf_path

    def parse(self) -> TaxFolder:
        t0 = time.perf_counter()
        source = str(Path(self.pdf_path).resolve())

        extractor = PDFExtractor()
        detector = SectionDetector()
        contributor_parser = ContributorParser()
        f29_parser = F29Parser()
        f22_parser = F22Parser()
        activities_parser = EconomicActivitiesParser()
        corporate_parser = CorporateParser()
        rule_engine = RuleEngine()
        kpi_engine = KPIEngine()
        tax_analyzer = TaxAnalyzer()
        tax_folder_mapper = TaxFolderMapper()
        f29_financial_parser = F29FinancialParser()
        monthly_tax_service = MonthlyTaxService()

        extract_result = extractor.extract(self.pdf_path)
        section_result = detector.detect(extract_result)
        contributor = contributor_parser.parse(extract_result, section_result)
        f29_forms = f29_parser.parse(extract_result, section_result)
        f22_forms = f22_parser.parse(extract_result, section_result)
        monthly_taxes = f29_financial_parser.parse(f29_forms)
        monthly_analysis = monthly_tax_service.analyze(monthly_taxes)
        activities = activities_parser.parse(extract_result, section_result)
        corporate = corporate_parser.parse(extract_result, section_result)

        tax_folder = TaxFolder(
            contributor=contributor,
            activities=activities,
            f29=f29_forms,
            f22=f22_forms,
            monthly_taxes=monthly_taxes,
            corporate=corporate,
            monthly_analysis=monthly_analysis,
            metadata=Metadata(
                source_file=source,
                pages=len(extract_result.pages),
                processing_time=0.0,
            ),
        )

        validation = rule_engine.run(tax_folder)
        tax_folder.validation = validation
        tax_folder.kpis = kpi_engine.calculate(tax_folder)
        company = tax_folder_mapper.map(tax_folder)
        tax_folder.analysis = tax_analyzer.analyze(company)
        tax_folder.metadata.processing_time = round(time.perf_counter() - t0, 3)

        return tax_folder
