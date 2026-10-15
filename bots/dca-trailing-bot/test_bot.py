#!/usr/bin/env python3
"""Script de test pour le DCA Trailing Bot."""

import sys
from pathlib import Path

# Ajouter le chemin parent au path
sys.path.insert(0, str(Path(__file__).parent))

from backtest import run_backtest
from config import BotConfig, load_config
from datetime import datetime


def test_backtest():
    """Test le backtest."""
    print("🔄 Test du backtest en cours...")
    
    # Créer une config minimale
    config_dict = {
        "mode": "paper",
        "market": {
            "product_id": "BTC-USDC",
            "granularity": "SIX_HOUR",
            "warmup_bars": 500,
        },
        "strategy": {
            "dca_levels": 3,
            "dca_percentage": 0.33,
            "dca_delay_bars": 6,
            "dca_pullback_levels": [-5.0, -10.0, -15.0],
            "trailing_stop_percentage": 10.0,
            "initial_stop_percentage": 15.0,
            "take_profit_r_multiple": 3.0,
            "use_trend_filter": True,
            "trend_ema": 200,
            "trend_slope_lookback": 20,
            "breakout_lookback": 20,
            "adx_period": 14,
            "adx_min": 20.0,
        },
        "risk": {
            "risk_per_trade": 0.01,
            "max_position_pct": 1.0,
        },
        "paper": {
            "starting_cash": 10000.0,
        },
        "discord": {
            "enabled": False,
        },
    }
    
    # Charger la config
    config = load_config()
    
    print(f"Configuration chargée: {config.mode}")
    print(f"Produit: {config.market.product_id}")
    print(f"Granularité: {config.market.granularity}")
    
    # Exécuter un backtest court
    print("\n📊 Backtest sur 90 jours...")
    try:
        result = run_backtest(config, days=90, product_id="BTC-USDC")
        print("\n" + result.summary())
        print("\n✅ Backtest terminé avec succès!")
        return result
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = test_backtest()
    if result:
        print("\n🎉 Test réussi!")
