#!/usr/bin/env python3
"""Génère les rapports Discord finaux avec les meilleures stratégies.

Ce script:
1. Teste les meilleures stratégies sur BTC et ETH
2. Génère des rapports avec graphiques comparant Stratégie vs Buy & Hold
3. Met en évidence les points d'entrée/sortie
4. Affiche clairement les performances

Utilisation:
    python generate_final_reports.py
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s | %(message)s')
log = logging.getLogger(__name__)

# Stratégies à tester pour chaque token
BTC_STRATEGIES = [
    'bull_rider_optimized_6h',
    'bull_rider_aggressive_6h',
    'bull_rider_max_6h',
]

ETH_STRATEGIES = [
    'eth_safe_6h',
    'eth_balanced_6h',
    'bull_rider_6h',
    'ema_cross_6h',
]


def run_backtest(product, strategy, days=730):
    """Exécute un backtest et retourne les stats."""
    try:
        cmd = [
            sys.executable, '-m', 'bot',
            '-p', product,
            'backtest',
            '--strategy', strategy,
            '--days', str(days)
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=150
        )
        
        # Parser les résultats
        output = result.stdout
        stats = {}
        
        for line in output.split('\n'):
            line = line.strip()
            if ':' in line:
                parts = line.split(':')
                key = parts[0].strip()
                value = ':'.join(parts[1:]).strip()
                
                if key == 'Performance':
                    stats['perf'] = float(value.replace('%', '').replace('+', ''))
                elif key == 'Buy & Hold':
                    stats['bh'] = float(value.replace('%', '').replace('+', ''))
                elif key == 'Max drawdown':
                    stats['mdd'] = float(value.replace('%', ''))
                elif key == 'CAGR':
                    stats['cagr'] = float(value.replace('%', '').replace('+', ''))
                elif key == 'Trades':
                    # Extraire le nombre
                    try:
                        stats['trades'] = int(value.split('(')[0].strip())
                        # Extraire win rate
                        if '(' in value:
                            wr_part = value.split('(')[1]
                            stats['win_rate'] = float(wr_part.split('%')[0].strip())
                    except (ValueError, IndexError):
                        pass
                elif key == 'Sharpe':
                    stats['sharpe'] = float(value.split()[0])
                elif key == 'Capital final':
                    stats['final_equity'] = float(value.replace(',', '').split()[0])
                elif key == 'Capital initial':
                    stats['initial_equity'] = float(value.replace(',', '').split()[0])
        
        if 'perf' in stats:
            stats['excess'] = stats['perf'] - stats['bh']
        
        return stats
    except Exception as e:
        log.error(f"Erreur backtest {product}/{strategy}: {e}")
        return None


def generate_report_text(product, strategy, stats):
    """Génère le texte du rapport pour Discord."""
    if not stats or 'perf' not in stats:
        return f"❌ Impossible de générer le rapport pour {product}/{strategy}"
    
    excess = stats.get('excess', 0)
    beats_bh = "✅ **BAT**" if excess > 0 else "❌ Ne bat pas"
    
    text = f"""📊 **RAPPORT {product} - {strategy}**

📈 **PERFORMANCE**
• Période: 730 jours (2024-08-15 → 2026-10-16)
• Capital initial: {stats.get('initial_equity', '10,000'):,.2f} USDC
• **Capital final: {stats.get('final_equity', 'N/A'):,.2f} USDC ({stats.get('perf', 0):+.2f}%)**
• Buy & Hold: {stats.get('bh', 0):+.2f}%
• **{beats_bh} le Buy & Hold: {excess:+.2f}%**

📉 **RISQUE**
• Max Drawdown: {stats.get('mdd', 0):.2f}%
• Sharpe: {stats.get('sharpe', 0):.2f}
• CAGR: {stats.get('cagr', 0):+.2f}%

🎯 **STATISTIQUES TRADES**
• Nombre de trades: {stats.get('trades', 'N/A')}
• Win Rate: {stats.get('win_rate', 0):.1f}%

💡 **CONCLUSION**: {beats_bh} le Buy & Hold sur cette période
"""
    return text


def main():
    log.info("Génération des rapports finaux...")
    
    # Créer le dossier de sortie
    output_dir = Path('reports')
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    
    all_reports = {}
    
    # Tester BTC
    log.info("\n" + "="*60)
    log.info("Testing BTC-USDC...")
    log.info("="*60)
    
    btc_best = None
    btc_best_excess = -999
    
    for strategy in BTC_STRATEGIES:
        log.info(f"  Testing {strategy}...")
        stats = run_backtest('BTC-USDC', strategy, 730)
        if stats and 'excess' in stats:
            if stats['excess'] > btc_best_excess:
                btc_best = strategy
                btc_best_excess = stats['excess']
                btc_best_stats = stats
            log.info(f"    {strategy}: Excess={stats['excess']:+.2f}% MDD={stats.get('mdd', 'N/A'):.2f}%")
    
    if btc_best:
        log.info(f"  Meilleure stratégie BTC: {btc_best} (Excess: {btc_best_excess:+.2f}%)")
    
    # Tester ETH
    log.info("\n" + "="*60)
    log.info("Testing ETH-USDC...")
    log.info("="*60)
    
    eth_best = None
    eth_best_excess = -999
    eth_lowest_mdd = 999
    
    for strategy in ETH_STRATEGIES:
        log.info(f"  Testing {strategy}...")
        stats = run_backtest('ETH-USDC', strategy, 730)
        if stats and 'excess' in stats:
            # Priorité: bat le BH (excess > 0) ET MDD le plus faible
            if stats['excess'] > 0:
                if stats.get('mdd', 999) < eth_lowest_mdd:
                    eth_best = strategy
                    eth_best_excess = stats['excess']
                    eth_best_stats = stats
                    eth_lowest_mdd = stats.get('mdd', 999)
            log.info(f"    {strategy}: Excess={stats['excess']:+.2f}% MDD={stats.get('mdd', 'N/A'):.2f}%")
    
    if eth_best:
        log.info(f"  Meilleure stratégie ETH: {eth_best} (Excess: {eth_best_excess:+.2f}%, MDD: {eth_lowest_mdd:.2f}%)")
    
    # Générer les rapports
    log.info("\n" + "="*60)
    log.info("Génération des rapports...")
    log.info("="*60)
    
    # Rapport BTC
    if btc_best and btc_best_stats:
        btc_report = generate_report_text('BTC-USDC', btc_best, btc_best_stats)
        print(btc_report)
        
        # Générer le graphique
        chart_cmd = [
            sys.executable, 'generate_discord_report.py',
            '--product', 'BTC-USDC',
            '--strategy', btc_best,
            '--days', '730'
        ]
        subprocess.run(chart_cmd, capture_output=True, text=True)
        
        all_reports['BTC-USDC'] = {
            'strategy': btc_best,
            'stats': btc_best_stats,
            'report_text': btc_report
        }
    
    # Rapport ETH
    if eth_best and eth_best_stats:
        eth_report = generate_report_text('ETH-USDC', eth_best, eth_best_stats)
        print(eth_report)
        
        # Générer le graphique
        chart_cmd = [
            sys.executable, 'generate_discord_report.py',
            '--product', 'ETH-USDC',
            '--strategy', eth_best,
            '--days', '730'
        ]
        subprocess.run(chart_cmd, capture_output=True, text=True)
        
        all_reports['ETH-USDC'] = {
            'strategy': eth_best,
            'stats': eth_best_stats,
            'report_text': eth_report
        }
    
    # Rapport comparatif final
    print("\n" + "="*60)
    print("📊 **RAPPORT FINAL COMPARATIF**")
    print("="*60)
    
    if 'BTC-USDC' in all_reports and 'ETH-USDC' in all_reports:
        btc = all_reports['BTC-USDC']
        eth = all_reports['ETH-USDC']
        
        print(f"\n🟦 **BTC-USDC**")
        print(f"   Stratégie: {btc['strategy']}")
        print(f"   Excess vs Buy & Hold: {btc['stats'].get('excess', 0):+.2f}%")
        print(f"   Max Drawdown: {btc['stats'].get('mdd', 0):.2f}%")
        
        print(f"\n🟦 **ETH-USDC**")
        print(f"   Stratégie: {eth['strategy']}")
        print(f"   Excess vs Buy & Hold: {eth['stats'].get('excess', 0):+.2f}%")
        print(f"   Max Drawdown: {eth['stats'].get('mdd', 0):.2f}%")
        
        print(f"\n💡 **COMMANDES POUR LANCER LE PAPER TRADING:**")
        print(f"   BTC: python -m bot -p BTC-USDC paper --strategy {btc['strategy']}")
        print(f"   ETH: python -m bot -p ETH-USDC paper --strategy {eth['strategy']}")
    
    # Sauvegarder les rapports
    report_file = output_dir / f'rapport_final_{timestamp}.json'
    with open(report_file, 'w') as f:
        json.dump(all_reports, f, indent=2, default=str, ensure_ascii=False)
    
    log.info(f"\n✅ Rapports sauvegardés: {report_file}")
    log.info(f"✅ Graphiques générés dans: {output_dir.absolute()}")


if __name__ == '__main__':
    main()
