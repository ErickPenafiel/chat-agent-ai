import pytest
import yaml
from pydantic import ValidationError

from src.core.config import TenantConfig, load_tenant_config

EXAMPLE = "config/tenant.example.yaml"


def _raw():
    return yaml.safe_load(open(EXAMPLE, encoding="utf-8"))


def test_loads_example():
    cfg = load_tenant_config(EXAMPLE)
    assert cfg.intents["sales"].capture_before_answer is False
    assert cfg.intents["support"].capture_fields == []


def test_intents_normalized_lowercase():
    raw = _raw()
    raw["intents"]["Ventas"] = {}
    assert "ventas" in TenantConfig.model_validate(raw).intents


def test_missing_required_fields_rejected():
    for key in ("business_name", "tone", "thresholds", "channels", "intents"):
        raw = _raw()
        del raw[key]
        with pytest.raises(ValidationError):
            TenantConfig.model_validate(raw)


def test_requires_escalate_and_chat():
    raw = _raw()
    del raw["intents"]["escalate"]
    with pytest.raises(ValidationError):
        TenantConfig.model_validate(raw)


def test_unknown_key_rejected():
    raw = _raw()
    raw["bussiness_name"] = "typo"
    with pytest.raises(ValidationError):
        TenantConfig.model_validate(raw)


def test_categories_normalized_and_deduped():
    raw = _raw()
    raw["categories"] = ["Payments", "shipping"]
    assert TenantConfig.model_validate(raw).categories == ["payments", "shipping"]
    raw["categories"] = ["Payments", "payments"]
    with pytest.raises(ValidationError):
        TenantConfig.model_validate(raw)
