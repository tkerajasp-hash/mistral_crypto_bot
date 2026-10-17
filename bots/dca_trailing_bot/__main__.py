"""DCA Trailing Bot - Point d'entrée CLI.

Commandes disponibles :

    # Vérifier l'accès aux données (public, pas de clé requise)
    python -m dca_trailing_bot fetch --days 10
    
    # Vérifier la connexion API Coinbase
    python -m dca_trailing_bot account
    
    # Backtest la stratégie
    python -m dca_trailing_bot backtest --days 365 --product BTC-USDC
    
    # Paper trading (simulation sur prix réels)
    python -m dca_trailing_bot paper --once
    
    # Live trading (vrais ordres - ATTENTION)
    python -m dca_trailing_bot live --i-understand-live-trading --once
    
    # Générer un rapport avec graphiques
    python -m dca_trailing_bot report --days 90
    
    # Voir l'état actuel
    python -m dca_trailing_bot status

Option globale : -p / --product BTC-USDC | ETH-USDC
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml
from dotenv import load_dotenv

# Charger les modules locaux
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from strategy import DCATrailingStrategy, DCAState
from backtest import run_backtest, BacktestResult
from report import generate_report, send_discord_report
from coinbase_client import MarketData

log = logging.getLogger("dca_trailing_bot")


def setup_logging(level: str = "INFO") -> None:
    """Configure le logging."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/dca_bot.log"),
        ],
    )


def load_config_file(config_path: str = "config.yaml") -> dict:
    """Charge la configuration depuis le fichier YAML."""
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
    
    return config


def create_strategy(config: dict) -> DCATrailingStrategy:
    """Crée la stratégie depuis la configuration."""
    strat_config = config.get("strategy", {})
    return DCATrailingStrategy(
        dca_levels=strat_config.get("dca_levels", 3),
        dca_percentage=strat_config.get("dca_percentage", 0.33),
        dca_delay_bars=strat_config.get("dca_delay_bars", 6),
        dca_pullback_levels=strat_config.get("dca_pullback_levels", [-5.0, -10.0, -15.0]),
        trailing_stop_pct=strat_config.get("trailing_stop_percentage", 10.0),
        initial_stop_pct=strat_config.get("initial_stop_percentage", 15.0),
        take_profit_r_multiple=strat_config.get("take_profit_r_multiple", 3.0),
        trend_ema=strat_config.get("trend_ema", 200),
        trend_slope_lookback=strat_config.get("trend_slope_lookback", 20),
        breakout_lookback=strat_config.get("breakout_lookback", 20),
        adx_period=strat_config.get("adx_period", 14),
        adx_min=strat_config.get("adx_min", 20.0),
        use_trend_filter=strat_config.get("use_trend_filter", True),
    )


def cmd_fetch(config: dict, args: argparse.Namespace) -> None:
    """Vérifie l'accès aux données de marché."""
    m = config.get("market", {})
    product_id = args.product or m.get("product_id", "BTC-USDC")
    granularity = m.get("granularity", "SIX_HOUR")
    
    gran_map = {
        "ONE_MINUTE": 60,
        "FIVE_MINUTE": 300,
        "FIFTEEN_MINUTE": 900,
        "THIRTY_MINUTE": 1800,
        "ONE_HOUR": 3600,
        "TWO_HOUR": 7200,
        "SIX_HOUR": 21600,
        "ONE_DAY": 86400,
    }
    gran_seconds = gran_map.get(granularity, 3600)
    
    md = MarketData()
    n = int(args.days * 86400 / gran_seconds) + 100
    df = md.get_candles(product_id, granularity, gran_seconds, n)
    
    print(f"✅ {len(df)} bougies {granularity} pour {product_id}")
    print(f"   Période: {df.index[0]} à {df.index[-1]}")
    print(f"\nDernières bougies:")
    print(df.tail(5).to_string())
    print(f"\nPrix spot actuel: ${md.spot_price(product_id):,.2f}")


def cmd_backtest(config: dict, args: argparse.Namespace) -> None:
    """Exécute un backtest."""
    # Charger la configuration complète
    full_config = load_config(args.config)
    
    product_id = args.product or full_config.market.product_id
    days = args.days
    
    print(f"\n🔄 Backtest en cours...")
    print(f"   Produit: {product_id}")
    print(f"   Période: {days} jours")
    print(f"   Stratégie: DCA + Trailing Stop 10%")
    print(f"   DCA: 3 niveaux à 33% (pullbacks: -5%, -10%, -15%)")
    
    # Exécuter le backtest
    result = run_backtest(full_config, days=days, product_id=product_id)
    
    # Afficher le résumé
    print(result.summary())
    
    # Générer le rapport si demandé
    if args.report:
        report_path = generate_report(result, full_config, product_id)
        print(f"\n✅ Rapport généré: {report_path}")
        
        # Envoyer sur Discord si configuré
        if full_config.discord.enabled and full_config.discord.send_backtest_results:
            send_discord_report(result, full_config, product_id, is_backtest=True)


def cmd_paper(config: dict, args: argparse.Namespace) -> None:
    """Paper trading (simulation)."""
    full_config = load_config(args.config)
    
    if full_config.mode != "paper":
        full_config.mode = "paper"
    
    print(f"\n📄 Paper Trading démarré")
    print(f"   Produit: {full_config.market.product_id}")
    print(f"   Capital: ${full_config.paper.starting_cash:,.2f}")
    print(f"   Mode: {full_config.mode}")
    
    # Pour l'instant, on exécute un backtest sur les dernières données
    # comme simulation de paper trading
    result = run_backtest(full_config, days=7, product_id=full_config.market.product_id)
    print(result.summary())
    
    # Envoyer sur Discord si configuré
    if full_config.discord.enabled:
        send_discord_report(result, full_config, full_config.market.product_id, is_backtest=False)


def cmd_live(config: dict, args: argparse.Namespace) -> None:
    """Live trading (vrais ordres)."""
    if not args.i_understand_live_trading:
        sys.exit("❌ Refusé: ajoute --i-understand-live-trading pour trader en réel.")
    
    full_config = load_config(args.config)
    
    if full_config.mode != "live":
        sys.exit("❌ Refusé: mets 'mode: live' dans config.yaml.")
    
    if not full_config.secrets.get("api_key") or not full_config.secrets.get("api_secret"):
        sys.exit("❌ Refusé: clés COINBASE_API_KEY / COINBASE_API_SECRET absentes de .env.")
    
    print("⚠️  LIVE TRADING NON IMPLÉMENTÉ ENCORE")
    print("   Pour l'instant, utilisez le mode 'paper' ou 'backtest'")
    print("   L'implémentation live viendra dans la Phase 2")


def cmd_report(config: dict, args: argparse.Namespace) -> None:
    """Génère un rapport avec graphiques."""
    full_config = load_config(args.config)
    product_id = args.product or full_config.market.product_id
    days = args.days
    
    print(f"\n📊 Génération du rapport...")
    print(f"   Produit: {product_id}")
    print(f"   Période: {days} jours")
    
    # Exécuter un backtest pour générer le rapport
    result = run_backtest(full_config, days=days, product_id=product_id)
    
    # Générer le rapport avec graphiques
    report_path = generate_report(result, full_config, product_id)
    print(f"\n✅ Rapport généré: {report_path}")
    
    # Envoyer sur Discord si configuré
    if full_config.discord.enabled:
        send_discord_report(result, full_config, product_id, is_backtest=False)
        print(f"✅ Rapport envoyé sur Discord")


def cmd_status(config: dict, args: argparse.Namespace) -> None:
    """Affiche l'état actuel."""
    print("\n📋 État du bot:")
    print(f"   Mode: {config.get('mode', 'paper')}")
    print(f"   Produit: {config.get('market', {}).get('product_id', 'BTC-USDC')}")
    print(f"   Granularité: {config.get('market', {}).get('granularity', 'SIX_HOUR')}")
    print(f"   Capital: ${config.get('paper', {}).get('starting_cash', 10000):,.2f}")
    print("\n⚠️  Le suivi d'état en temps réel viendra dans la Phase 2")


def cmd_discord_test(config: dict, args: argparse.Namespace) -> None:
    """Test l'envoi Discord."""
    # Charger la config complète
    full_config = load_config(args.config if hasattr(args, 'config') else "config.yaml")
    
    if not full_config.discord.enabled:
        print("❌ Discord non activé dans config.yaml")
        return
    
    webhook_url = full_config.discord.webhook_url
    if not webhook_url:
        print("❌ webhook_url non configuré dans config.yaml")
        return
    
    print("\n📤 Test Discord...")
    
    # Créer un faux résultat pour le test
    from backtest import BacktestResult, Trade
    from datetime import datetime, timedelta
    
    trades = []
    now = datetime.now()
    for i in range(5):
        entry_time = now - timedelta(days=90-i*10)
        exit_time = entry_time + timedelta(days=5)
        trades.append(Trade(
            entry_time=entry_time,
            exit_time=exit_time,
            entry_price=50000 + i*1000,
            exit_price=52000 + i*1000,
            quantity=0.01,
            entry_fee=2.5,
            exit_fee=2.5,
            pnl=195.0,
            r_multiple=1.5,
            reason=f"Test trade {i+1}"
        ))
    
    result = BacktestResult(
        equity_curve=pd.Series([10000 + i*200 for i in range(100)]),
        trades=trades,
        stats={
            "start": (now - timedelta(days=90)).strftime("%Y-%m-%d"),
            "end": now.strftime("%Y-%m-%d"),
            "days": 90,
            "start_equity": 10000,
            "end_equity": 12000,
            "total_return_pct": 20.0,
            "cagr_pct": 8.5,
            "buy_hold_pct": 25.0,
            "max_drawdown_pct": 5.0,
            "sharpe": 1.2,
            "n_trades": 5,
            "win_rate_pct": 100.0,
            "avg_win": 195.0,
            "avg_loss": 0.0,
            "avg_r": 1.5,
            "profit_factor": float("inf"),
            "total_fees": 25.0,
            "time_in_market_pct": 50.0,
        }
    )
    
    try:
        send_discord_report(result, full_config, "BTC-USDC", is_backtest=True)
        print("✅ Message de test envoyé sur Discord avec succès !")
    except Exception as e:
        print(f"❌ Erreur: {e}")


def main() -> None:
    """Point d'entrée principal."""
    p = argparse.ArgumentParser(
        prog="dca_trailing_bot",
        description="Bot de trading DCA + Trailing Stop pour Coinbase",
    )
    p.add_argument("--config", default="config.yaml", help="Fichier de configuration")
    p.add_argument("-p", "--product", default=None,
                   help="Paire à trader (ex: BTC-USDC, ETH-USDC)")
    
    sub = p.add_subparsers(dest="cmd", required=True)
    
    # fetch
    sp = sub.add_parser("fetch", help="Vérifie l'accès aux données")
    sp.add_argument("--days", type=int, default=30)
    sp.set_defaults(func=cmd_fetch)
    
    # backtest
    sp = sub.add_parser("backtest", help="Exécute un backtest")
    sp.add_argument("--days", type=int, default=365)
    sp.add_argument("--report", action="store_true", help="Génère un rapport")
    sp.set_defaults(func=cmd_backtest)
    
    # paper
    sp = sub.add_parser("paper", help="Paper trading (simulation)")
    sp.add_argument("--once", action="store_true")
    sp.set_defaults(func=cmd_paper)
    
    # live
    sp = sub.add_parser("live", help="Live trading (vrais ordres)")
    sp.add_argument("--once", action="store_true")
    sp.add_argument("--i-understand-live-trading", action="store_true")
    sp.set_defaults(func=cmd_live)
    
    # report
    sp = sub.add_parser("report", help="Génère un rapport avec graphiques")
    sp.add_argument("--days", type=int, default=90)
    sp.set_defaults(func=cmd_report)
    
    # status
    sp = sub.add_parser("status", help="Affiche l'état actuel")
    sp.set_defaults(func=cmd_status)
    
    # discord-test
    sp = sub.add_parser("discord-test", help="Test l'envoi Discord")
    sp.set_defaults(func=cmd_discord_test)
    
    args = p.parse_args()
    
    # Charger la configuration
    try:
        config = load_config_file(args.config)
    except Exception as e:
        sys.exit(f"❌ Erreur de chargement config: {e}")
    
    # Charger les secrets depuis .env
    load_dotenv()
    config["secrets"] = {
        "api_key": os.getenv("COINBASE_API_KEY"),
        "api_secret": os.getenv("COINBASE_API_SECRET"),
    }
    
    # Configurer le logging
    setup_logging(config.get("logging", {}).get("level", "INFO"))
    
    # Exécuter la commande
    args.func(config, args)


if __name__ == "__main__":
    main()
