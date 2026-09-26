import re
from pathlib import Path
from src.extractors.pdf_extractor import PDFExtractor
from src.detectors.section_detector import SectionDetector

def inspect_all():
    extractor = PDFExtractor()
    detector = SectionDetector()
    pdf_paths = sorted(Path("examples").glob("*.pdf")) + sorted(Path("tests/fixtures_validate").glob("*.pdf"))
    
    print(f"Total PDFs found: {len(pdf_paths)}")
    
    for pdf_path in pdf_paths:
        try:
            res = extractor.extract(pdf_path)
            sec = detector.detect(res)
        except Exception as e:
            print(f"Error reading {pdf_path.name}: {e}")
            continue
            
        print(f"\n==========================================")
        print(f"PDF: {pdf_path.name} ({len(res.pages)} pages)")
        
        # Check F22 pages
        f22_pages = sec.secciones.get("FORMULARIO 22", [])
        print(f"F22 pages: {f22_pages}")
        if f22_pages:
            f22_text = "\n".join(res.pages[p - 1].text for p in f22_pages if p - 1 < len(res.pages))
            # Find lines matching numbers/codes
            print("--- F22 Matches ---")
            for line in f22_text.split("\n"):
                # Search for CPT, RLI, Ingresos keywords or known codes
                if any(kw in line.upper() for kw in ["CAPITAL PROPIO", "RENTA L", "BASE IMPONIBLE", "INGRESOS", "PERDIDA", "PERMUT"]) or \
                   re.search(r"\b(844|645|1545|1702|646|843|1546|1694|1109|1409|1414|1438|1695|1143|1415|1657|628|1400|1430|305|36|82)\b", line):
                    print(f"   {line.strip()}")
                    
        # Check F29 codes
        f29_pages = sec.secciones.get("FORMULARIO 29", [])
        print(f"F29 pages: {len(f29_pages)}")
        if f29_pages:
            sample_text = res.pages[f29_pages[0] - 1].text
            print("--- Sample F29 first page lines matching compras/credito/retencion ---")
            for line in sample_text.split("\n"):
                if re.search(r"\b(511|520|524|525|527|528|536|514|562|584|504|048|151|755|756|779|094)\b", line):
                    print(f"   {line.strip()}")

if __name__ == "__main__":
    inspect_all()
