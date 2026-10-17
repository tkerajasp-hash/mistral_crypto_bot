"""Notifications Telegram (texte + image).

Best-effort par conception : toute erreur reseau / config est logguee puis avalee,
jamais propagee. Un probleme d'envoi ne doit JAMAIS interrompre la boucle de trading.

Mise en place :
  1. cree un bot via @BotFather -> recupere le token
  2. ecris un message a ton bot, puis recupere ton chat_id
     (ex. https://api.telegram.org/bot<token>/getUpdates , ou @userinfobot)
  3. .env :  TELEGRAM_BOT_TOKEN=...   TELEGRAM_CHAT_ID=...
  4. config.yaml :  notifications.enabled: true
"""
from __future__ import annotations

import html
import logging
from pathlib import Path

import requests

log = logging.getLogger("bot.notify")

_API = "https://api.telegram.org"


def esc(value) -> str:
    """Echappe un champ dynamique pour le parse_mode HTML de Telegram."""
    return html.escape(str(value), quote=False)


class Notifier:
    def __init__(
        self,
        token: str | None,
        chat_id: str | None,
        *,
        enabled: bool = True,
        timeout: int = 10,
    ):
        self.token = (token or "").strip()
        self.chat_id = (chat_id or "").strip()
        self.timeout = timeout
        self.enabled = bool(enabled and self.token and self.chat_id)
        if enabled and not self.enabled:
            log.warning(
                "notifications.enabled=true mais TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID "
                "manquant(s) dans .env -> notifications desactivees."
            )

    # -- bas niveau --------------------------------------------------------
    def _post(self, method: str, *, data: dict, files: dict | None = None) -> bool:
        if not self.enabled:
            return False
        try:
            r = requests.post(
                f"{_API}/bot{self.token}/{method}",
                data=data,
                files=files,
                timeout=self.timeout,
            )
            if r.status_code != 200:
                log.warning("Telegram %s -> HTTP %s : %s", method, r.status_code, r.text[:200])
                return False
            return True
        except Exception as exc:  # noqa: BLE001
            log.warning("Telegram %s a echoue : %s", method, exc)
            return False

    # -- haut niveau -----------------------------------------------------
    def send(self, text: str) -> bool:
        """Envoie un message texte (parse_mode HTML)."""
        return self._post(
            "sendMessage",
            data={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )

    def send_photo(self, image_path: str | Path, caption: str = "") -> bool:
        """Envoie une image. `caption` est tronquee a 1024 caracteres (limite Telegram)."""
        p = Path(image_path)
        if not p.exists():
            log.warning("Image introuvable, envoi ignore : %s", p)
            return False
        try:
            with p.open("rb") as fh:
                return self._post(
                    "sendPhoto",
                    data={
                        "chat_id": self.chat_id,
                        "caption": caption[:1024],
                        "parse_mode": "HTML",
                    },
                    files={"photo": fh},
                )
        except Exception as exc:  # noqa: BLE001
            log.warning("Envoi photo a echoue : %s", exc)
            return False


def from_config(cfg) -> Notifier:
    """Construit un Notifier a partir de la config (secrets .env + notifications.enabled)."""
    return Notifier(
        getattr(cfg.secrets, "telegram_token", None),
        getattr(cfg.secrets, "telegram_chat_id", None),
        enabled=cfg.notifications.enabled,
    )


def disabled() -> Notifier:
    """Un Notifier inerte (aucun envoi), pour les contextes sans notifications."""
    return Notifier(None, None, enabled=False)
