"""Test ULTIMATE Configuration - DCA Trailing Bot.

Ce test vérifie que la nouvelle configuration bat le Buy & Hold
avec un drawdown minimal sur BTC-USDC et ETH-USDC.

Nouvelles améliorations testées:
1. DCA sur les FONDS DISPONIBLES (pas capital initial)
2. Confirmation de la baisse avec RSI/EMA avant DCA
3. Double filtre de tendance (EMA200 + EMA50)
4. Pullbacks par rapport au PLUS HAUT (pas prix d'entrée)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from backtest import run_backtest


def run_ultimate_test(product_id: str = "BTC-USDC", days: int = 365):
    """Exécute un backtest avec la configuration ULTIME."""
    print(f"\n{'='*70}")
    print(f"  TEST ULTIMATE - {product_id} - {days} jours")
    print(f"{'='*70}\n")
    
    # Charger la config ultimate (spécifique pour ETH)
    if product_id == "ETH-USDC":
        config = load_config("config_eth_ultimate.yaml")
    else:
        config = load_config("config_ultimate.yaml")
    
    # Override product_id
    config.market.product_id = product_id
    
    # Exécuter le backtest
    result = run_backtest(config, days=days, product_id=product_id)
    
    # Afficher les résultats
    print(result.summary())
    
    # Vérifier les critères de succès
    stats = result.stats
    
    print("\n" + "="*70)
    print("  CRITÈRES DE SUCCÈS")
    print("="*70)
    
    # Comparaison avec Buy & Hold
    btc_return = stats.get('total_return_pct', 0)
    btc_bh = stats.get('buy_hold_pct', 0)
    diff_vs_bh = btc_return - btc_bh
    
    print(f"\nPerformance vs Buy & Hold: {btc_return:+.2f}% vs {btc_bh:+.2f}%")
    print(f"Écart: {diff_vs_bh:+.2f}%")
    
    if diff_vs_bh > 0:
        print("✓ MEILLEUR que Buy & Hold")
    else:
        print("✗ PAS MEILLEUR que Buy & Hold - IL FAUT AMÉLIORER!")
    
    # Drawdown
    max_dd = stats.get('max_drawdown_pct', 0)
    print(f"\nMax Drawdown: {max_dd:.2f}%")
    
    if max_dd < 15:
        print("✓ Drawdown ACCEPTABLE (< 15%)")
    elif max_dd < 20:
        print("⚠ Drawdown ÉLEVÉ (15-20%)")
    else:
        print("✗ Drawdown TROP ÉLEVÉ (> 20%) - IL FAUT RÉDUIRE!")
    
    # Nombre de trades
    n_trades = stats.get('n_trades', 0)
    print(f"\nNombre de trades: {n_trades}")
    
    if n_trades >= 5:
        print("✓ Activité suffisante")
    else:
        print("⚠ Peu de trades - vérifier les conditions d'entrée")
    
    # Temps en position
    time_in_market = stats.get('time_in_market_pct', 0)
    print(f"\nTemps en position: {time_in_market:.1f}%")
    
    if time_in_market >= 30:
        print("✓ Bon temps d'exposition au marché")
    else:
        print("⚠ Peu de temps en position")
    
    # Résumé final
    print("\n" + "="*70)
    if diff_vs_bh > 0 and max_dd < 20:
        print(f"  ✓✓✓ SUCCÈS: {product_id} - Bat B&H avec drawdown contrôlé!")
    elif diff_vs_bh > 0:
        print(f"  ✓✓  BON: {product_id} - Bat B&H mais drawdown élevé")
    else:
        print(f"  ✗✗✗ ÉCHEC: {product_id} - Ne bat pas B&H ou drawdown trop élevé")
    print("="*70 + "\n")
    
    return result, diff_vs_bh, max_dd


def main():
    """Exécute les tests sur BTC-USDC et ETH-USDC."""
    print("\n" + "="*70)
    print("  DÉMARRAGE DES TESTS ULTIMATE")
    print("  Configuration: config_ultimate.yaml")
    print("="*70 + "\n")
    
    results = {}
    
    # Test BTC-USDC
    btc_result, btc_diff, btc_dd = run_ultimate_test("BTC-USDC", days=365)
    results["BTC-USDC"] = {"diff_vs_bh": btc_diff, "max_dd": btc_dd, "result": btc_result}
    
    # Test ETH-USDC
    eth_result, eth_diff, eth_dd = run_ultimate_test("ETH-USDC", days=365)
    results["ETH-USDC"] = {"diff_vs_bh": eth_diff, "max_dd": eth_dd, "result": eth_result}
    
    # Résumé global
    print("\n" + "="*70)
    print("  RÉSUMÉ GLOBAL")
    print("="*70)
    
    btc_success = btc_diff > 0 and btc_dd < 20
    eth_success = eth_diff > 0 and eth_dd < 20
    
    print(f"\nBTC-USDC: {'✓ SUCCÈS' if btc_success else '✗ ÉCHEC'} (vs B&H: {btc_diff:+.2f}%, DD: {btc_dd:.2f}%)")
    print(f"ETH-USDC: {'✓ SUCCÈS' if eth_success else '✗ ÉCHEC'} (vs B&H: {eth_diff:+.2f}%, DD: {eth_dd:.2f}%)")
    
    if btc_success and eth_success:
        print("\n" + "="*70)
        print("  ✓✓✓ TOUS LES TESTS RÉUSSIS!")
        print("  La stratégie bat le Buy & Hold sur les deux tokens!")
        print("="*70 + "\n")
        return 0
    else:
        print("\n" + "="*70)
        print("  ⚠⚠⚠ IL FAUT AMÉLIORER LA STRATÉGIE")
        if not btc_success:
            print("  - BTC-USDC: Problème de performance ou drawdown")
        if not eth_success:
            print("  - ETH-USDC: Problème de performance ou drawdown")
        print("="*70 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
