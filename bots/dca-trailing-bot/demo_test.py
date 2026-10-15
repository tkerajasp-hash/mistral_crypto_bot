#!/usr/bin/env python3
"""
Démonstration du DCA Trailing Bot avec données simulées.

Ce script montre comment le bot fonctionne avec des données de prix simulées.
Il génère un rapport complet avec graphiques.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np

# Ajouter le dossier courant au path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from backtest import DCABacktester, BacktestResult
from config import BotConfig, load_config
from report import generate_report, generate_image_report


def generate_test_data(days: int = 365, product_id: str = "BTC-USDC") -> pd.DataFrame:
    """Génère des données de test réalistes.
    
    Simule un marché avec :
    - Une tendance haussière globale
    - Des pullbacks pour déclencher le DCA
    - De la volatilité réaliste
    """
    n_bars = days * 4  # 4 bougies par jour (6H)
    dates = pd.date_range(end=datetime.now(), periods=n_bars, freq='6H')
    
    # Générer une tendance haussière de base
    trend = np.linspace(40000, 50000, n_bars)
    
    # Ajouter des variations aléatoires
    np.random.seed(42)
    noise = np.random.normal(0, 500, n_bars)
    
    # Ajouter des pullbacks significatifs pour déclencher le DCA
    pullback_points = [int(n_bars * 0.1), int(n_bars * 0.4), int(n_bars * 0.7)]
    for point in pullback_points:
        # Pullback de -10% à -15%
        if point < n_bars:
            for i in range(point, min(point + 5, n_bars)):
                trend[i] *= 0.85  # -15%
    
    # Générer les prix
    close = trend + noise
    
    # Calculer OHLC
    high = close + np.random.normal(200, 100, n_bars)
    low = close - np.random.normal(200, 100, n_bars)
    open_p = close - np.random.normal(50, 50, n_bars)
    
    # S'assurer que high > close > low
    high = np.maximum(high, close + 10)
    low = np.minimum(low, close - 10)
    
    # Volume
    volume = np.random.randint(1000, 10000, n_bars)
    
    # Créer le DataFrame
    df = pd.DataFrame({
        'open': open_p,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    }, index=dates)
    
    return df


def create_test_config() -> BotConfig:
    """Crée une configuration de test."""
    return BotConfig(
        mode="paper",
        market=type('obj', (object,), {
            'product_id': 'BTC-USDC',
            'granularity': 'SIX_HOUR',
            'warmup_bars': 100,
        })(),
        strategy=type('obj', (object,), {
            'dca_levels': 3,
            'dca_percentage': 0.33,
            'dca_delay_bars': 1,  # 1 bougie pour le test
            'dca_pullback_levels': [-5.0, -10.0, -15.0],
            'trailing_stop_percentage': 10.0,
            'initial_stop_percentage': 15.0,
            'take_profit_r_multiple': 2.0,  # Take profit plus proche
            'use_trend_filter': False,  # Désactiver pour le test
            'initial_entry_condition': 'donchian_breakout',
            'breakout_lookback': 5,  # Plus court pour déclencher plus souvent
            'trend_ema': 200,
            'trend_slope_lookback': 20,
            'adx_period': 14,
            'adx_min': 0.0,  # Désactiver ADX pour le test
        })(),
        paper=type('obj', (object,), {
            'starting_cash': 10000.0,
        })(),
    )


def main():
    """Exécute la démonstration."""
    print("=" * 70)
    print("       DÉMONSTRATION - DCA TRAILING BOT")
    print("=" * 70)
    print("\n📊 Génération de données de test...")
    
    # Générer les données
    df = generate_test_data(days=90)
    print(f"   {len(df)} bougies générées")
    print(f"   Période: {df.index[0].date()} → {df.index[-1].date()}")
    print(f"   Prix: ${df['close'].min():.2f} → ${df['close'].max():.2f}")
    
    # Créer le config
    config = create_test_config()
    
    # Créer un backtester personnalisé avec données simulées
    class TestBacktester(DCABacktester):
        def _fetch_data(self, product_id: str, days: int) -> pd.DataFrame:
            return df
    
    # Exécuter le backtest
    print("\n🔄 Backtest en cours...")
    backtester = TestBacktester(config)
    result = backtester.run("BTC-USDC", days=90)
    
    # Afficher le résumé
    print("\n" + result.summary())
    
    # Générer les graphiques
    print("\n📈 Génération des graphiques...")
    try:
        images = generate_image_report(result, config, "BTC-USDC", "demo")
        print(f"   ✅ Signaux: {images['signals']}")
        print(f"   ✅ PnL: {images['pnl']}")
        
        # Afficher les paths
        for img_type, path in images.items():
            if path and Path(path).exists():
                print(f"\n   📊 {img_type.upper()}: {path}")
                # Afficher la taille
                size = Path(path).stat().st_size / 1024
                print(f"      Taille: {size:.1f} KB")
        
        print("\n✅ Démo terminée avec succès!")
        print("\n💡 Pour configurer Discord:")
        print("   1. Créez un Webhook Discord (Paramètres → Intégrations → Webhooks)")
        print("   2. Copiez l'URL du webhook")
        print("   3. Ajoutez dans config.yaml:")
        print("      discord:")
        print("        enabled: true")
        print("        webhook_url: VOTRE_URL")
        print("   4. Exécutez: python -m dca_trailing_bot backtest --days 90 --report")
        
    except Exception as e:
        print(f"\n⚠️  Erreur graphique: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
