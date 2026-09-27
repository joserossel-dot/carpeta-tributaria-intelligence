import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.leads.lead_manager import LeadManager, LeadRecord, validar_email


class TestLeadValidation:
    def test_validar_email_formatos(self):
        assert validar_email("juan@empresa.cl") is True
        assert validar_email("maria.gonzalez@holding.com") is True
        assert validar_email("contacto+b2b@cavilaria.cl") is True

        assert validar_email("") is False
        assert validar_email("invalido") is False
        assert validar_email("sin_arroba.cl") is False
        assert validar_email("@sin_usuario.cl") is False
        assert validar_email(None) is False


class TestLeadManager:
    def test_registrar_lead_exitoso(self, tmp_path):
        leads_file = tmp_path / "leads_test.json"
        lm = LeadManager(leads_file)

        lead = lm.registrar_lead(
            nombre="Alfonso Rossel",
            empresa="Cavilaria SpA",
            email="alfonso@cavilaria.com",
            telefono="+56 9 9999 8888",
        )

        assert isinstance(lead, LeadRecord)
        assert lead.nombre == "Alfonso Rossel"
        assert lead.empresa == "Cavilaria SpA"
        assert lead.email == "alfonso@cavilaria.com"
        assert lead.access_tier == "FREE_TRIAL"
        assert len(lead.id) == 12

        # Verificar persistencia en archivo
        leads = lm.obtener_leads()
        assert len(leads) == 1
        assert leads[0]["email"] == "alfonso@cavilaria.com"

    def test_registrar_lead_actualiza_si_existe_email(self, tmp_path):
        leads_file = tmp_path / "leads_test.json"
        lm = LeadManager(leads_file)

        lm.registrar_lead(
            nombre="Juan Original",
            empresa="Empresa 1",
            email="repetido@empresa.com",
        )
        lm.registrar_lead(
            nombre="Juan Actualizado",
            empresa="Empresa 2",
            email="repetido@empresa.com",
        )

        leads = lm.obtener_leads()
        assert len(leads) == 1
        assert leads[0]["nombre"] == "Juan Actualizado"
        assert leads[0]["empresa"] == "Empresa 2"

    def test_validaciones_campos_obligatorios(self, tmp_path):
        lm = LeadManager(tmp_path / "leads_test.json")

        with pytest.raises(ValueError, match="nombre completo es obligatorio"):
            lm.registrar_lead("", "Empresa", "test@test.cl")

        with pytest.raises(ValueError, match="empresa es obligatoria"):
            lm.registrar_lead("Nombre", "", "test@test.cl")

        with pytest.raises(ValueError, match="correo electrónico no tiene un formato válido"):
            lm.registrar_lead("Nombre", "Empresa", "email_invalido")

    def test_exportar_csv_y_json(self, tmp_path):
        leads_file = tmp_path / "leads_test.json"
        lm = LeadManager(leads_file)

        lm.registrar_lead("Cliente 1", "Empresa A", "c1@empresa.cl")
        lm.registrar_lead("Cliente 2", "Empresa B", "c2@empresa.cl")

        # CSV
        csv_bytes = lm.exportar_csv()
        csv_text = csv_bytes.decode("utf-8-sig")
        assert "Cliente 1" in csv_text
        assert "Cliente 2" in csv_text
        assert "Empresa A" in csv_text
        assert "c1@empresa.cl" in csv_text

        # JSON
        json_bytes = lm.exportar_json()
        data = json.loads(json_bytes.decode("utf-8"))
        assert len(data) == 2
        assert data[0]["nombre"] == "Cliente 1"

    @patch("urllib.request.urlopen")
    def test_webhook_dispatches_lead(self, mock_urlopen, tmp_path, monkeypatch):
        monkeypatch.setenv("LEADS_WEBHOOK_URL", "https://crm.example.com/webhook")
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        lm = LeadManager(tmp_path / "leads_test.json")
        lm.registrar_lead("Lead Webhook", "Startup SpA", "lead@startup.cl")

        assert mock_urlopen.called
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://crm.example.com/webhook"
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["evento"] == "NUEVO_LEAD_FREEMIUM"
        assert payload["lead"]["email"] == "lead@startup.cl"
