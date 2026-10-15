"""Configuración de negocio (tenant). Obligatoria: no hay defaults de ningún negocio."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.core.intents import REQUIRED_INTENTS, normalize_intent


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Tone(_Strict):
    formality: Literal["formal", "informal"]
    address_form: str  # ej. "usted", "tú", "vos"
    language: str  # ej. "es"


class Thresholds(_Strict):
    sla_hours: float = Field(gt=0)
    session_timeout_minutes: int = Field(gt=0)


class IntentConfig(_Strict):
    capture_fields: list[str] = []
    # Default false: responder primero, capturar datos del lead después.
    capture_before_answer: bool = False


class LLMConfig(_Strict):
    provider: Literal["google", "anthropic", "groq"]
    model: str = Field(min_length=1)  # explícito: los nombres de modelo cambian y no se asume uno
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=1024, gt=0)
    timeout_seconds: float = Field(default=30, gt=0)


class AuthConfig(_Strict):
    """Autenticación de la API de administración (Firebase Auth)."""

    mode: Literal["firebase", "disabled"]
    firebase_project_id: str | None = None
    # Quién es admin: correos (con email verificado en Firebase) o el custom claim `admin: true`.
    admin_emails: list[str] = []
    require_email_verified: bool = True

    @field_validator("admin_emails")
    @classmethod
    def _lower_emails(cls, v):
        return [e.strip().lower() for e in v]

    @model_validator(mode="after")
    def _firebase_needs_project(self):
        if self.mode == "firebase" and not self.firebase_project_id:
            raise ValueError("auth.firebase_project_id es obligatorio con mode: firebase")
        return self


class CorsConfig(_Strict):
    # Orígenes del frontend, explícitos. Vacío = sin CORS (solo mismo origen).
    allowed_origins: list[str] = []

    @field_validator("allowed_origins")
    @classmethod
    def _explicit_origins(cls, v):
        if any(o.strip() == "*" for o in v):
            raise ValueError("cors.allowed_origins no admite '*': lista los orígenes explícitos")
        return [o.strip().rstrip("/") for o in v]


class TenantConfig(_Strict):
    business_name: str = Field(min_length=1)
    tone: Tone
    thresholds: Thresholds
    intents: dict[str, IntentConfig]
    # Temas de la KB (ej. "pagos", "envíos"). Distintos de las intenciones; opcionales.
    categories: list[str] = []
    auth: AuthConfig  # obligatorio: la API de administración nunca queda abierta por omisión
    cors: CorsConfig = CorsConfig()
    channels: list[str] = Field(min_length=1)
    connectors: list[str] = []
    llm: LLMConfig | None = None  # sin llm el agente responde en crudo (sin generación)
    media_enabled: bool = False
    # Guardrail anti-alucinación: un LLM compara la respuesta con la KB/datos antes de enviarla (+1 llamada por turno).
    verify_responses: bool = False
    max_input_chars: int = Field(default=2000, gt=0)  # tope por mensaje: protege la cuota del LLM
    identity_entity_type: str | None = None  # "equipo", "pedido", "cuenta", "turno"…

    @field_validator("intents", mode="before")
    @classmethod
    def _normalize_intents(cls, v):
        if not isinstance(v, dict):
            return v
        out = {}
        for key, cfg in v.items():
            norm = normalize_intent(key)
            if norm in out:
                raise ValueError(f"intención duplicada tras normalizar: {norm!r}")
            out[norm] = cfg if cfg is not None else {}
        return out

    @field_validator("categories")
    @classmethod
    def _normalize_categories(cls, v):
        out = [normalize_intent(c) for c in v]
        if len(set(out)) != len(out):
            raise ValueError("categorías duplicadas tras normalizar")
        return out

    @model_validator(mode="after")
    def _required_intents(self):
        missing = [i for i in REQUIRED_INTENTS if i not in self.intents]
        if missing:
            raise ValueError(f"intenciones obligatorias faltantes: {missing}")
        return self


def load_tenant_config(path: str | Path) -> TenantConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return TenantConfig.model_validate(data)
