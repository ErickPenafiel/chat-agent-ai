"""Exporta el esquema OpenAPI de la API (de ahí el frontend genera sus tipos). No necesita servidor ni LLM.
Uso: uv run python -m scripts.export_openapi ../agent-ai-frontend/openapi.json"""

import json
import os
import sys

# El esquema no depende de la autenticación; el modo abierto solo evita exigir Firebase para exportarlo.
os.environ.setdefault("ALLOW_INSECURE_AUTH", "1")

from src.api.app import create_app
from src.core.config import load_tenant_config


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    app = create_app(load_tenant_config("config/tenant.example.yaml"), "sqlite:///:memory:")
    with open(sys.argv[1], "w", encoding="utf-8") as f:
        json.dump(app.openapi(), f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    print(f"OpenAPI escrito en {sys.argv[1]}")


if __name__ == "__main__":
    main()
