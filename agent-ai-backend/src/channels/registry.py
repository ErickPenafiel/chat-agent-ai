"""Fábrica de canales según `channels` de tenant.yaml. Los secretos salen del entorno, nunca del YAML."""

import os
from collections.abc import Callable, Mapping

from src.channels.base import MessagingChannel
from src.channels.web import WebChannel
from src.channels.whatsapp_cloud_api import WhatsAppCloudAPIChannel


def _whatsapp(env: Mapping[str, str]) -> MessagingChannel:
    required = ("WHATSAPP_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_APP_SECRET", "WHATSAPP_VERIFY_TOKEN")
    missing = [k for k in required if not env.get(k)]
    if missing:
        raise RuntimeError(f"faltan variables de entorno para whatsapp_cloud_api: {missing}")
    return WhatsAppCloudAPIChannel(
        access_token=env["WHATSAPP_TOKEN"],
        phone_number_id=env["WHATSAPP_PHONE_NUMBER_ID"],
        app_secret=env["WHATSAPP_APP_SECRET"],
        verify_token=env["WHATSAPP_VERIFY_TOKEN"],
    )


FACTORIES: dict[str, Callable[[Mapping[str, str]], MessagingChannel]] = {
    "web": lambda env: WebChannel(),
    "whatsapp_cloud_api": _whatsapp,
}


def build_channels(names: list[str], env: Mapping[str, str] | None = None) -> dict[str, MessagingChannel]:
    env = os.environ if env is None else env
    unknown = [n for n in names if n not in FACTORIES]
    if unknown:
        raise ValueError(f"canales desconocidos en tenant.yaml: {unknown}; disponibles: {sorted(FACTORIES)}")
    return {n: FACTORIES[n](env) for n in names}
