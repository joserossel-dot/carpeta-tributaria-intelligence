from src.models.company import Company
from src.models.tax_folder import TaxFolder


class TaxFolderMapper:
    def map(self, tax_folder: TaxFolder) -> Company:
        return Company(
            contributor=tax_folder.contributor,
            activities=tax_folder.activities,
            representatives=tax_folder.representatives,
            properties=tax_folder.properties,
            vehicles=tax_folder.vehicles,
            f29=tax_folder.f29,
            f22=tax_folder.f22,
            kpis=tax_folder.kpis,
            analysis=tax_folder.analysis,
            monthly_taxes=tax_folder.monthly_taxes,
            monthly_analysis=tax_folder.monthly_analysis,
        )
