"""Gestor de Leads y Registro Instantáneo Freemium B2B.

Captura y persiste los datos de prospectos comerciales que solicitan
acceso de prueba gratuita (2 evaluaciones) y notifica al equipo comercial.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

_DEFAULT_LEADS_PATH = Path(__file__).resolve().parents[2] / "data" / "leads_registrados.json"
EMAIL_REGEX = re.compile(r"^[\w\.\+-]+@[\w\.-]+\.\w+$")


class LeadRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    nombre: str
    empresa: str
    email: str
    telefono: str | None = None
    fecha_registro: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    access_tier: str = "FREE_TRIAL"
    evaluaciones_realizadas: int = 0


def validar_email(email: str) -> bool:
    """Verifica si el formato del correo electrónico es válido."""
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


def _enviar_webhook_lead(lead: LeadRecord) -> bool:
    """Notifica al webhook comercial si está configurado."""
    webhook_url = os.environ.get("LEADS_WEBHOOK_URL") or os.environ.get("TELEMETRY_WEBHOOK_URL")
    if not webhook_url:
        return False

    try:
        payload = {
            "evento": "NUEVO_LEAD_FREEMIUM",
            "lead": lead.model_dump(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Cavilaria-Leads/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status < 300
    except Exception:
        # Falla silenciosa: la notificación jamás debe bloquear al usuario
        return False


class LeadManager:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or _DEFAULT_LEADS_PATH
        self._leads: list[dict] = self._load()

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._leads, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def registrar_lead(
        self,
        nombre: str,
        empresa: str,
        email: str,
        telefono: str | None = None,
    ) -> LeadRecord:
        """Registra un nuevo prospecto en el sistema."""
        nombre_clean = nombre.strip()
        empresa_clean = empresa.strip()
        email_clean = email.strip().lower()
        telefono_clean = telefono.strip() if telefono else None

        if not nombre_clean:
            raise ValueError("El nombre completo es obligatorio.")
        if not empresa_clean:
            raise ValueError("La empresa es obligatoria.")
        if not validar_email(email_clean):
            raise ValueError("El correo electrónico no tiene un formato válido.")

        # Buscar si ya existe para actualizar o reingresar
        lead = LeadRecord(
            nombre=nombre_clean,
            empresa=empresa_clean,
            email=email_clean,
            telefono=telefono_clean,
        )

        # Actualizar si existe el mismo email o agregar nuevo
        idx = next((i for i, item in enumerate(self._leads) if item.get("email") == email_clean), None)
        if idx is not None:
            self._leads[idx].update(lead.model_dump())
        else:
            self._leads.append(lead.model_dump())

        self._save()
        _enviar_webhook_lead(lead)
        return lead

    def obtener_leads(self) -> list[dict]:
        """Retorna la lista de leads registrados."""
        return list(self._leads)

    def exportar_csv(self) -> bytes:
        """Exporta los prospectos a CSV con codificación utf-8-sig para Excel."""
        output = io.StringIO()
        fieldnames = ["id", "fecha_registro", "nombre", "empresa", "email", "telefono", "access_tier", "evaluaciones_realizadas"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for item in self._leads:
            writer.writerow({k: item.get(k, "") for k in fieldnames})
        return output.getvalue().encode("utf-8-sig")

    def exportar_json(self) -> bytes:
        """Exporta los prospectos a JSON formateado."""
        return json.dumps(self._leads, indent=2, ensure_ascii=False).encode("utf-8")
