from datetime import datetime, timezone

from src.detectors.section_detector import SectionDetector
from src.extractors.pdf_extractor import PDFExtractor
from src.models.tax_folder import TaxFolder
from src.parsers.contributor_parser import ContributorParser
from src.parsers.f29_parser import F29Parser


class TaxFolderEngine:
    """Orquesta la extracción, detección y parsing de una carpeta tributaria."""

    VERSION = "0.1.0"

    def __init__(self, pdf_path: str) -> None:
        self.pdf_path = pdf_path

    def parse(self) -> TaxFolder:
        extractor = PDFExtractor()
        detector = SectionDetector()
        contributor_parser = ContributorParser()
        f29_parser = F29Parser()

        extract_result = extractor.extract(self.pdf_path)
        section_result = detector.detect(extract_result)
        contributor = contributor_parser.parse(extract_result, section_result)
        f29_forms = f29_parser.parse(extract_result, section_result)

        return TaxFolder(
            contributor=contributor,
            f29=f29_forms,
            sections=section_result,
            metadata={
                "pages": len(extract_result.pages),
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "version": self.VERSION,
            },
        )
