"""Chargement et validation de la configuration (YAML + secrets .env)."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_PRODUCT_RE = re.compile(r"^[A-Z0-9]+-[A-Z0-9]+$")

import yaml
from dotenv import load_dotenv

VALID_GRANULARITIES = {
    "ONE_MINUTE": 60,
    "FIVE_MINUTE": 300,
    "FIFTEEN_MINUTE": 900,
    "THIRTY_MINUTE": 1800,
    "ONE_HOUR": 3600,
    "TWO_HOUR": 7200,
    "SIX_HOUR": 21600,
    "ONE_DAY": 86400,
}


@dataclass
class MarketConfig:
    product_id: str = "BTC-USDC"
    granularity: str = "ONE_HOUR"
    warmup_bars: int = 400

    @property
    def granularity_seconds(self) -> int:
        return VALID_GRANULARITIES[self.granularity]


@dataclass
class StrategyConfig:
    entry_mode: str = "donchian_breakout"  # donchian_breakout | ema_cross | pullback | breakout_or_pullback
    regime_mode: str = "strict"            # strict (prix>EMA + pente>0) | fast (prix>EMA + EMA_fast>EMA_slow)
    trend_ema: int = 200
    trend_slope_lookback: int = 20
    breakout_lookback: int = 20
    ema_fast: int = 20
    ema_slow: int = 50
    pullback_lookback: int = 5   # nb de bougies pour reperer un repli sur l'EMA rapide (mode pullback)
    adx_period: int = 14
    adx_min: float = 22.0
    htf_filter: bool = True
    htf_granularity: str = "ONE_DAY"
    htf_ema: int = 50
    exit_lookback: int = 10


@dataclass
class RiskConfig:
    risk_per_trade: float = 0.0075
    max_position_pct: float = 0.95
    atr_period: int = 14
    initial_stop_atr: float = 2.5
    trailing_atr: float = 3.0
    breakeven_at_r: float = 1.0
    breakeven_offset_atr: float = 0.25
    hard_max_loss_pct: float = 0.06
    daily_max_loss_pct: float = 0.04
    max_drawdown_pct: float = 0.25
    # Stop "crash bougie" : si le rendement d'UNE bougie cloturee <= -bar_crash_stop_pct
    # (ex. 0.05 = -5% sur une 6h), sortie immediate au marche. 0 = desactive.
    bar_crash_stop_pct: float = 0.0

    # --- Pilotage dynamique de l'exposition (bot/exposure.py) --------------
    # Desactive par defaut : n'affecte que les presets qui mettent exposure_control: true.
    exposure_control: bool = False
    # 1) vol targeting : taille *= clip(vol_ref / ATR%_courant, floor, cap)
    vol_target_pct: float = 0.0          # 0 = vol_ref glissante (mediane) ; sinon cible ATR% fixe
    vol_target_lookback: int = 1460     # bougies pour la mediane glissante d'ATR% (~1 an en 6h)
    vol_mult_floor: float = 0.25
    vol_mult_cap: float = 1.0            # 1.0 = on ne leviere jamais au-dela du risk_per_trade de base
    # 2) frein de krach : sortie/blocage si chute brutale
    crash_return_bars: int = 3          # rendement sur N bougies
    crash_return_atr: float = 3.0       # ... < -(crash_return_atr * ATR%)  -> frein
    crash_ema_atr: float = 2.0          # ou close < EMA(ema_fast) - crash_ema_atr * ATR -> frein
    crash_brake_bars: int = 8           # le frein reste actif N bougies apres le declenchement
    # 3) throttle de drawdown : reduit lineairement la taille au-dela de dd_throttle_start
    dd_throttle_start: float = 0.10     # a partir de -10% du pic d'equity
    dd_throttle_floor: float = 0.30     # taille minimale (30%) atteinte a -2*start
    # 4) anti-whipsaw : taille reduite juste apres une sortie
    whipsaw_bars: int = 12
    whipsaw_mult: float = 0.5


@dataclass
class FeeConfig:
    maker_bps: float = 0.0
    taker_bps: float = 0.0
    assumed_roundtrip_bps: float = 10.0
    slippage_bps: float = 2.0


@dataclass
class ExecutionConfig:
    prefer_maker: bool = True
    limit_offset_bps: float = 5.0
    order_timeout_sec: int = 45
    stop_exit_is_market: bool = True
    cooldown_bars: int = 3
    min_edge_atr: float = 1.0
    poll_offset_sec: int = 20


@dataclass
class PaperConfig:
    starting_cash: float = 10_000.0


@dataclass
class NotificationsConfig:
    enabled: bool = False       # true = envoie sur Telegram (token/chat_id dans .env)
    on_trades: bool = True      # alerte a chaque ENTREE / SORTIE
    on_incidents: bool = True   # alerte pause journaliere / kill switch


@dataclass
class LoggingConfig:
    level: str = "INFO"
    state_file: str = "state/bot_state.json"
    trades_csv: str = "logs/trades.csv"
    equity_csv: str = "logs/equity.csv"


@dataclass
class Secrets:
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    @property
    def present(self) -> bool:
        return bool(self.api_key and self.api_secret)


@dataclass
class BotConfig:
    mode: str = "paper"
    active_strategy: Optional[str] = None   # nom du preset applique (voir strategies.yaml)
    market: MarketConfig = field(default_factory=MarketConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    fees: FeeConfig = field(default_factory=FeeConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    paper: PaperConfig = field(default_factory=PaperConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    secrets: Secrets = field(default_factory=Secrets)

    # ------------------------------------------------------------------
    def validate(self) -> None:
        if self.mode not in ("paper", "live"):
            raise ValueError(f"mode invalide: {self.mode!r} (paper|live)")
        if not _PRODUCT_RE.match(self.market.product_id):
            raise ValueError(
                f"product_id invalide: {self.market.product_id!r} "
                "(format BASE-QUOTE en majuscules, ex. BTC-USDC ou ETH-USDC)"
            )
        if self.market.granularity not in VALID_GRANULARITIES:
            raise ValueError(f"granularity invalide: {self.market.granularity}")
        if self.strategy.htf_granularity not in VALID_GRANULARITIES:
            raise ValueError(f"htf_granularity invalide: {self.strategy.htf_granularity}")
        if not 0 < self.risk.risk_per_trade < 0.2:
            raise ValueError("risk_per_trade doit etre dans ]0, 0.2[")
        if not 0 < self.risk.max_position_pct <= 1:
            raise ValueError("max_position_pct doit etre dans ]0, 1]")
        if self.risk.initial_stop_atr <= 0 or self.risk.trailing_atr <= 0:
            raise ValueError("les multiples ATR doivent etre > 0")
        if self.strategy.entry_mode not in (
            "donchian_breakout", "ema_cross", "pullback", "breakout_or_pullback"
        ):
            raise ValueError("entry_mode: donchian_breakout|ema_cross|pullback|breakout_or_pullback")
        if self.strategy.regime_mode not in ("strict", "fast"):
            raise ValueError("regime_mode: strict|fast")
        if self.mode == "live" and not self.secrets.present:
            raise ValueError("mode live: COINBASE_API_KEY / COINBASE_API_SECRET manquants dans .env")


def runtime_path(path: str | os.PathLike, product_id: str) -> str:
    """Insere le produit dans un nom de fichier : state/bot_state.json -> state/bot_state_BTC-USDC.json.

    Permet de faire tourner BTC-USDC et ETH-USDC en parallele sans que leurs
    etats / journaux / sorties de backtest se marchent dessus.
    """
    p = Path(path)
    return str(p.with_name(f"{p.stem}_{product_id}{p.suffix}"))


def _merge(dc, data: dict):
    """Applique les cles connues de `data` sur la dataclass `dc`."""
    if not data:
        return dc
    known = dc.__dataclass_fields__
    for key, value in data.items():
        if key in known and not hasattr(value, "items"):
            setattr(dc, key, value)
    return dc


def _deep_merge(base: dict, override: dict) -> dict:
    """Fusion recursive de dicts (override gagne). Ne modifie pas les entrees."""
    out = dict(base or {})
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def list_strategies(strategies_path: str | os.PathLike = "strategies.yaml") -> tuple[Optional[str], dict]:
    """Renvoie (nom_actif, {nom: preset_dict}) depuis strategies.yaml."""
    p = Path(strategies_path)
    if not p.exists():
        return None, {}
    spec = yaml.safe_load(p.read_text()) or {}
    return spec.get("active"), spec.get("presets", {}) or {}


def load_config(
    path: str | os.PathLike = "config.yaml",
    *,
    env_path: str = ".env",
    strategy_name: Optional[str] = None,
    strategies_path: str | os.PathLike = "strategies.yaml",
    product: Optional[str] = None,
) -> BotConfig:
    load_dotenv(env_path)
    raw = {}
    p = Path(path)
    if p.exists():
        raw = yaml.safe_load(p.read_text()) or {}

    active, presets = list_strategies(strategies_path)
    chosen = strategy_name or active
    if chosen:
        if chosen not in presets:
            raise ValueError(
                f"strategie inconnue: {chosen!r}. Disponibles: {', '.join(presets) or '(aucune)'}"
            )
        raw = _deep_merge(raw, presets[chosen])

    cfg = BotConfig()
    cfg.mode = raw.get("mode", cfg.mode)
    cfg.active_strategy = chosen
    _merge(cfg.market, raw.get("market", {}))
    _merge(cfg.strategy, raw.get("strategy", {}))
    _merge(cfg.risk, raw.get("risk", {}))
    _merge(cfg.fees, raw.get("fees", {}))
    _merge(cfg.execution, raw.get("execution", {}))
    _merge(cfg.paper, raw.get("paper", {}))
    _merge(cfg.notifications, raw.get("notifications", {}))
    _merge(cfg.logging, raw.get("logging", {}))

    if product:
        cfg.market.product_id = product
    cfg.market.product_id = cfg.market.product_id.strip().upper()

    cfg.secrets = Secrets(
        api_key=os.getenv("COINBASE_API_KEY") or None,
        api_secret=(os.getenv("COINBASE_API_SECRET") or "").replace("\\n", "\n") or None,
        telegram_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID") or None,
    )
    cfg.validate()

    # Fichiers d'execution nommes par produit (isolation BTC / ETH / ...).
    pid = cfg.market.product_id
    cfg.logging.state_file = runtime_path(cfg.logging.state_file, pid)
    cfg.logging.trades_csv = runtime_path(cfg.logging.trades_csv, pid)
    cfg.logging.equity_csv = runtime_path(cfg.logging.equity_csv, pid)
    return cfg
