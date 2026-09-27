from unittest.mock import MagicMock, patch
import pytest

from app.components.activities import show_activities
from app.components.alerts import show_alerts
from app.components.company_info import show_company_info
from app.components.corporate_info import show_corporate_info
from app.components.credit_score import show_credit_score
from app.components.downloads import show_downloads
from app.components.export_data import show_export
from app.components.f22_summary import show_f22_summary
from app.components.kpi_cards import show_kpi_cards
from app.components.monthly_chart import show_monthly_chart
from app.components.representatives import show_representatives
from src.core.tax_folder_engine import TaxFolderEngine
from src.models.contributor import Contributor
from src.models.tax_folder import Metadata, TaxFolder
from src.reports.executive_report import ExecutiveReport


def mock_columns(spec, **kwargs):
    if isinstance(spec, int):
        return [MagicMock() for _ in range(spec)]
    elif isinstance(spec, (list, tuple)):
        return [MagicMock() for _ in range(len(spec))]
    return [MagicMock()]


def mock_selectbox(label, options, index=0, **kwargs):
    if options:
        idx = min(index, len(options) - 1)
        return options[idx]
    return None


def mock_radio(label, options, index=0, **kwargs):
    if options:
        idx = min(index, len(options) - 1)
        return options[idx]
    return None


@pytest.fixture(autouse=True)
def mock_streamlit_ui():
    """Mock Streamlit UI elements to allow headless testing without browser."""
    with patch("streamlit.columns", side_effect=mock_columns), \
         patch("streamlit.selectbox", side_effect=mock_selectbox), \
         patch("streamlit.radio", side_effect=mock_radio), \
         patch("streamlit.metric"), \
         patch("streamlit.markdown"), \
         patch("streamlit.subheader"), \
         patch("streamlit.caption"), \
         patch("streamlit.info"), \
         patch("streamlit.warning"), \
         patch("streamlit.error"), \
         patch("streamlit.success"), \
         patch("streamlit.divider"), \
         patch("streamlit.dataframe"), \
         patch("streamlit.line_chart"), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.download_button", return_value=False), \
         patch("streamlit.expander", return_value=MagicMock()):
        yield


class TestUIComponentsWithRealData:
    @pytest.fixture(scope="class")
    def sample_folder_gonzalez(self):
        engine = TaxFolderEngine("examples/CPTAgrGonzalezLtda.pdf")
        return engine.parse()

    @pytest.fixture(scope="class")
    def sample_folder_exportadora(self):
        engine = TaxFolderEngine("examples/CPTExportadora.pdf")
        return engine.parse()

    def test_all_components_render_gonzalez(self, sample_folder_gonzalez):
        tf = sample_folder_gonzalez
        # Ensure no AttributeError or unhandled exception occurs
        show_kpi_cards(tf)
        show_company_info(tf)
        show_activities(tf)
        show_representatives(tf.representatives)
        show_corporate_info(tf)
        show_monthly_chart(tf)
        show_f22_summary(tf)
        show_credit_score(tf)
        show_alerts(tf)
        show_export(tf, auth_role="admin")
        show_export(tf, auth_role="client")
        show_downloads(b"{}", b"# Report")

        report = ExecutiveReport().generate(tf, tf.kpis, tf.analysis)
        assert isinstance(report, str)
        assert len(report) > 100

    def test_all_components_render_exportadora(self, sample_folder_exportadora):
        tf = sample_folder_exportadora
        show_kpi_cards(tf)
        show_company_info(tf)
        show_activities(tf)
        show_representatives(tf.representatives)
        show_corporate_info(tf)
        show_monthly_chart(tf)
        show_f22_summary(tf)
        show_credit_score(tf)
        show_alerts(tf)
        show_export(tf, auth_role="admin")
        show_export(tf, auth_role="client")

        report = ExecutiveReport().generate(tf, tf.kpis, tf.analysis)
        assert isinstance(report, str)
        assert len(report) > 100

    def test_all_components_with_empty_folder(self):
        """Test defensive behavior when TaxFolder has no data / None fields."""
        empty_tf = TaxFolder(
            metadata=Metadata(source_file="empty.pdf", pages=1, processing_time=0.0)
        )
        show_kpi_cards(empty_tf)
        show_company_info(empty_tf)
        show_activities(empty_tf)
        show_representatives(empty_tf.representatives)
        show_corporate_info(empty_tf)
        show_monthly_chart(empty_tf)
        show_f22_summary(empty_tf)
        show_credit_score(empty_tf)
        show_alerts(empty_tf)
        show_export(empty_tf, auth_role="admin")
        show_export(empty_tf, auth_role="client")
        show_downloads(b"{}", b"# Report")

        report = ExecutiveReport().generate(empty_tf, empty_tf.kpis, empty_tf.analysis)
        assert isinstance(report, str)

    def test_all_components_with_partial_folder(self):
        """Test with partial contributor, empty F22, empty monthly taxes."""
        partial_tf = TaxFolder(
            contributor=Contributor(
                rut="11.222.333-4",
                razon_social="TEST PARCIAL SPA",
            ),
            metadata=Metadata(source_file="partial.pdf", pages=1, processing_time=0.0),
        )
        show_kpi_cards(partial_tf)
        show_company_info(partial_tf)
        show_activities(partial_tf)
        show_representatives(partial_tf.representatives)
        show_corporate_info(partial_tf)
        show_monthly_chart(partial_tf)
        show_f22_summary(partial_tf)
        show_credit_score(partial_tf)
        show_alerts(partial_tf)
        show_export(partial_tf, auth_role="admin")
        show_export(partial_tf, auth_role="client")
