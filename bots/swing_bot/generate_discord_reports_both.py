#!/usr/bin/env python3
"""Script qui génère des rapports Discord pour BTC et ETH avec les meilleures stratégies.

Ce script:
1. Teste plusieurs stratégies sur BTC et ETH
2. Sélectionne celles qui battent le buy & hold
3. Génère des rapports comparatifs clairs

Utilisation :
    python generate_discord_reports_both.py
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from bot.backtest import run_backtest
from bot.config import load_config

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s | %(message)s')
log = logging.getLogger(__name__)

# Stratégies à tester
STRATEGIES = [
    'bull_rider_6h',
    'bull_rider_aggressive_6h', 
    'bull_rider_optimized_6h',
    'bull_rider_max_6h',
    'bull_rider_adaptive_6h',
    'bull_rider_guarded_6h',
]

PRODUCTS = ['BTC-USDC', 'ETH-USDC']


def run_all_backtests(days=730):
    """Exécute les backtests pour toutes les stratégies et produits."""
    results = {}
    
    for product in PRODUCTS:
        results[product] = {}
        for strategy in STRATEGIES:
            try:
                log.info(f"Backtest {strategy} sur {product}...")
                cfg = load_config(strategy_name=strategy, product=product)
                result = run_backtest(cfg, days=days, save_dir=None)
                results[product][strategy] = result.stats
            except Exception as e:
                log.error(f"Erreur avec {strategy}/{product}: {e}")
                results[product][strategy] = None
    
    return results


def find_best_strategies(results):
    """Trouve les meilleures stratégies pour chaque produit."""
    best = {}
    
    for product in PRODUCTS:
        best[product] = []
        for strategy, stats in results[product].items():
            if stats is None:
                continue
            excess = stats['total_return_pct'] - stats['buy_hold_pct']
            if excess > 0:  # Bat le buy & hold
                best[product].append({
                    'strategy': strategy,
                    'stats': stats,
                    'excess': excess
                })
        
        # Trier par excédent (meilleur d'abord)
        best[product].sort(key=lambda x: x['excess'], reverse=True)
    
    return best


def generate_combined_report(best_strategies):
    """Génère un rapport combiné pour Discord."""
    report_lines = []
    
    report_lines.append("📊 **RAPPORT STRATÉGIES - BTC vs ETH**")
    report_lines.append("=" * 50)
    report_lines.append("")
    
    for product in PRODUCTS:
        report_lines.append(f"🟦 **{product}**")
        report_lines.append("-" * 50)
        
        if not best_strategies[product]:
            report_lines.append("❌ Aucune stratégie ne bat le Buy & Hold")
        else:
            for i, item in enumerate(best_strategies[product][:3]):  # Top 3
                stats = item['stats']
                report_lines.append(
                    f"{i+1}. **{item['strategy']}**"
                )
                report_lines.append(
                    f"   • Performance: {stats['total_return_pct']:+.2f}% | "
                    f"Buy & Hold: {stats['buy_hold_pct']:+.2f}% | "
                    f"**Écart: {item['excess']:+.2f}%**"
                )
                report_lines.append(
                    f"   • Max Drawdown: {stats['max_drawdown_pct']:.2f}% | "
                    f"Sharpe: {stats['sharpe']:.2f}"
                )
                report_lines.append(
                    f"   • Trades: {stats['n_trades']} | Win Rate: {stats['win_rate_pct']:.1f}%"
                )
        
        report_lines.append("")
    
    # Résumé comparatif
    report_lines.append("📈 **RÉSUMÉ COMPARATIF**")
    report_lines.append("-" * 50)
    
    for product in PRODUCTS:
        if best_strategies[product]:
            best_strategy = best_strategies[product][0]
            stats = best_strategy['stats']
            report_lines.append(
                f"{product}: **{best_strategy['strategy']}** "
                f"(+{best_strategy['excess']:+.2f}% vs BH, MDD: {stats['max_drawdown_pct']:.2f}%)"
            )
    
    return "\n".join(report_lines)


def main():
    log.info("Début des backtests pour toutes les stratégies...")
    
    # Exécuter les backtests
    results = run_all_backtests(days=730)
    
    # Trouver les meilleures stratégies
    best_strategies = find_best_strategies(results)
    
    # Générer le rapport
    report = generate_combined_report(best_strategies)
    
    print("\n" + report + "\n")
    
    # Sauvegarder les résultats complets
    output_dir = Path('reports')
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    
    # Sauvegarder le rapport texte
    report_file = output_dir / f'comparatif_strategies_{timestamp}.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # Sauvegarder les données JSON
    json_file = output_dir / f'comparatif_data_{timestamp}.json'
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    log.info(f"✅ Rapport sauvegardé: {report_file}")
    log.info(f"✅ Données sauvegardées: {json_file}")


if __name__ == '__main__':
    main()
