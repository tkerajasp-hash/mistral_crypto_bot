"""Configuration pour le DCA Trailing Bot."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Ajouter le dossier courant au path
sys.path.insert(0, str(Path(__file__).parent))

import yaml
from dotenv import load_dotenv


@dataclass
class MarketConfig:
    product_id: str = "BTC-USDC"
    granularity: str = "SIX_HOUR"
    warmup_bars: int = 500


@dataclass
class StrategyConfig:
    # Mode d'entrée
    entry_mode: str = "dca_on_pullback"
    
    # DCA Configuration
    dca_levels: int = 3
    dca_percentage: float = 0.33
    dca_delay_bars: int = 6
    dca_pullback_levels: list[float] = field(default_factory=lambda: [-5.0, -10.0, -15.0])
    dca_use_atr_levels: bool = False
    dca_pullback_atr_multipliers: list[float] = field(default_factory=lambda: [1.5, 2.5, 3.5])
    
    # NOUVELLES OPTIONS: DCA sur fonds disponibles
    use_available_funds: bool = False
    dca_available_funds_percentage: float = 0.50
    
    # NOUVELLES OPTIONS: Confirmation DCA
    use_dca_confirmation: bool = False
    dca_confirmation_mode: str = "rsi_ema"
    
    # NOUVELLES OPTIONS: Filtre de tendance renforcé
    use_enhanced_trend_filter: bool = False
    trend_ema_fast: int = 50
    
    # NOUVELLES OPTIONS: RSI
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    confirm_ema_fast: int = 20
    
    # Entrée initiale
    initial_entry_condition: str = "donchian_breakout"
    breakout_lookback: int = 20
    
    # Filtre de tendance
    use_trend_filter: bool = True
    trend_ema: int = 200
    trend_slope_lookback: int = 20
    
    # ADX
    adx_period: int = 14
    adx_min: float = 20.0
    
    # Stops
    trailing_stop_percentage: float = 10.0
    initial_stop_percentage: float = 15.0
    
    # Take Profit
    take_profit_r_multiple: float = 3.0


@dataclass
class RiskConfig:
    risk_per_trade: float = 0.01
    max_position_pct: float = 1.0
    hard_max_loss_pct: float = 0.06
    daily_max_loss_pct: float = 0.04
    max_drawdown_pct: float = 0.20


@dataclass
class ExecutionConfig:
    prefer_maker: bool = True
    limit_offset_bps: float = 5.0
    order_timeout_sec: int = 45
    stop_exit_is_market: bool = True
    cooldown_bars: int = 3
    poll_offset_sec: int = 20


@dataclass
class PaperConfig:
    starting_cash: float = 10000.0


@dataclass
class NotificationsConfig:
    enabled: bool = False
    on_trades: bool = True
    on_incidents: bool = True


@dataclass
class DiscordConfig:
    enabled: bool = False
    webhook_url: Optional[str] = None
    send_trades: bool = True
    send_daily_report: bool = True
    send_backtest_results: bool = True


@dataclass
class LoggingConfig:
    level: str = "INFO"
    state_file: str = "state/bot_state.json"
    trades_csv: str = "logs/trades.csv"
    equity_csv: str = "logs/equity.csv"


@dataclass
class BotConfig:
    mode: str = "paper"
    market: MarketConfig = field(default_factory=MarketConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    paper: PaperConfig = field(default_factory=PaperConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)
    discord: DiscordConfig = field(default_factory=DiscordConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    secrets: dict = field(default_factory=dict)


def load_config(config_path: str = "config.yaml") -> BotConfig:
    """Charge la configuration depuis le fichier YAML et .env."""
    # Charger le fichier YAML
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(path) as f:
        raw_config = yaml.safe_load(f) or {}
    
    # Charger .env
    load_dotenv()
    
    # Créer la config
    config = BotConfig()
    
    # Appliquer les valeurs du YAML
    if "mode" in raw_config:
        config.mode = raw_config["mode"]
    
    # Market
    if "market" in raw_config:
        market = raw_config["market"]
        if "product_id" in market:
            config.market.product_id = market["product_id"]
        if "granularity" in market:
            config.market.granularity = market["granularity"]
        if "warmup_bars" in market:
            config.market.warmup_bars = market["warmup_bars"]
    
    # Strategy
    if "strategy" in raw_config:
        strat = raw_config["strategy"]
        if "entry_mode" in strat:
            config.strategy.entry_mode = strat["entry_mode"]
        if "initial_entry_condition" in strat:
            config.strategy.initial_entry_condition = strat["initial_entry_condition"]
        if "dca_levels" in strat:
            config.strategy.dca_levels = strat["dca_levels"]
        if "dca_percentage" in strat:
            config.strategy.dca_percentage = strat["dca_percentage"]
        if "dca_delay_bars" in strat:
            config.strategy.dca_delay_bars = strat["dca_delay_bars"]
        if "dca_pullback_levels" in strat:
            config.strategy.dca_pullback_levels = strat["dca_pullback_levels"]
        if "dca_use_atr_levels" in strat:
            config.strategy.dca_use_atr_levels = strat["dca_use_atr_levels"]
        if "dca_pullback_atr_multipliers" in strat:
            config.strategy.dca_pullback_atr_multipliers = strat["dca_pullback_atr_multipliers"]
        if "use_available_funds" in strat:
            config.strategy.use_available_funds = strat["use_available_funds"]
        if "dca_available_funds_percentage" in strat:
            config.strategy.dca_available_funds_percentage = strat["dca_available_funds_percentage"]
        if "use_dca_confirmation" in strat:
            config.strategy.use_dca_confirmation = strat["use_dca_confirmation"]
        if "dca_confirmation_mode" in strat:
            config.strategy.dca_confirmation_mode = strat["dca_confirmation_mode"]
        if "use_enhanced_trend_filter" in strat:
            config.strategy.use_enhanced_trend_filter = strat["use_enhanced_trend_filter"]
        if "trend_ema_fast" in strat:
            config.strategy.trend_ema_fast = strat["trend_ema_fast"]
        if "rsi_period" in strat:
            config.strategy.rsi_period = strat["rsi_period"]
        if "rsi_oversold" in strat:
            config.strategy.rsi_oversold = strat["rsi_oversold"]
        if "confirm_ema_fast" in strat:
            config.strategy.confirm_ema_fast = strat["confirm_ema_fast"]
        if "trailing_stop_percentage" in strat:
            config.strategy.trailing_stop_percentage = strat["trailing_stop_percentage"]
        if "initial_stop_percentage" in strat:
            config.strategy.initial_stop_percentage = strat["initial_stop_percentage"]
        if "take_profit_r_multiple" in strat:
            config.strategy.take_profit_r_multiple = strat["take_profit_r_multiple"]
        if "use_trend_filter" in strat:
            config.strategy.use_trend_filter = strat["use_trend_filter"]
        if "trend_ema" in strat:
            config.strategy.trend_ema = strat["trend_ema"]
        if "trend_slope_lookback" in strat:
            config.strategy.trend_slope_lookback = strat["trend_slope_lookback"]
        if "breakout_lookback" in strat:
            config.strategy.breakout_lookback = strat["breakout_lookback"]
        if "adx_period" in strat:
            config.strategy.adx_period = strat["adx_period"]
        if "adx_min" in strat:
            config.strategy.adx_min = strat["adx_min"]
    
    # Risk
    if "risk" in raw_config:
        risk = raw_config["risk"]
        if "risk_per_trade" in risk:
            config.risk.risk_per_trade = risk["risk_per_trade"]
        if "max_position_pct" in risk:
            config.risk.max_position_pct = risk["max_position_pct"]
        if "hard_max_loss_pct" in risk:
            config.risk.hard_max_loss_pct = risk["hard_max_loss_pct"]
        if "daily_max_loss_pct" in risk:
            config.risk.daily_max_loss_pct = risk["daily_max_loss_pct"]
        if "max_drawdown_pct" in risk:
            config.risk.max_drawdown_pct = risk["max_drawdown_pct"]
    
    # Execution
    if "execution" in raw_config:
        exec_config = raw_config["execution"]
        if "prefer_maker" in exec_config:
            config.execution.prefer_maker = exec_config["prefer_maker"]
        if "limit_offset_bps" in exec_config:
            config.execution.limit_offset_bps = exec_config["limit_offset_bps"]
        if "order_timeout_sec" in exec_config:
            config.execution.order_timeout_sec = exec_config["order_timeout_sec"]
        if "stop_exit_is_market" in exec_config:
            config.execution.stop_exit_is_market = exec_config["stop_exit_is_market"]
        if "cooldown_bars" in exec_config:
            config.execution.cooldown_bars = exec_config["cooldown_bars"]
        if "poll_offset_sec" in exec_config:
            config.execution.poll_offset_sec = exec_config["poll_offset_sec"]
    
    # Paper
    if "paper" in raw_config:
        paper = raw_config["paper"]
        if "starting_cash" in paper:
            config.paper.starting_cash = paper["starting_cash"]
    
    # Notifications
    if "notifications" in raw_config:
        notif = raw_config["notifications"]
        if "enabled" in notif:
            config.notifications.enabled = notif["enabled"]
        if "on_trades" in notif:
            config.notifications.on_trades = notif["on_trades"]
        if "on_incidents" in notif:
            config.notifications.on_incidents = notif["on_incidents"]
    
    # Discord
    if "discord" in raw_config:
        discord = raw_config["discord"]
        if "enabled" in discord:
            config.discord.enabled = discord["enabled"]
        if "webhook_url" in discord:
            config.discord.webhook_url = discord["webhook_url"]
        if "send_trades" in discord:
            config.discord.send_trades = discord["send_trades"]
        if "send_daily_report" in discord:
            config.discord.send_daily_report = discord["send_daily_report"]
        if "send_backtest_results" in discord:
            config.discord.send_backtest_results = discord["send_backtest_results"]
    
    # Logging
    if "logging" in raw_config:
        log = raw_config["logging"]
        if "level" in log:
            config.logging.level = log["level"]
        if "state_file" in log:
            config.logging.state_file = log["state_file"]
        if "trades_csv" in log:
            config.logging.trades_csv = log["trades_csv"]
        if "equity_csv" in log:
            config.logging.equity_csv = log["equity_csv"]
    
    # Secrets
    config.secrets = {
        "api_key": os.getenv("COINBASE_API_KEY"),
        "api_secret": os.getenv("COINBASE_API_SECRET"),
    }
    
    # Validation
    if config.strategy.dca_percentage * config.strategy.dca_levels > 1.0:
        raise ValueError("Total DCA allocation exceeds 100%")
    
    if config.strategy.trailing_stop_percentage <= 0:
        raise ValueError("Trailing stop percentage must be > 0")
    
    return config
