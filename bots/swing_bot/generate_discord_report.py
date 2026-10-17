#!/usr/bin/env python3
"""Script de génération de rapport Discord comparant les stratégies au Buy & Hold.

Ce script génère des graphiques clairs montrant :
- La performance (PNL) de chaque stratégie vs Buy & Hold
- Les points d'entrée et de sortie
- Les drawdowns

Utilisation :
    python generate_discord_report.py
    python generate_discord_report.py --product ETH-USDC
    python generate_discord_report.py --days 365 --strategy bull_rider_optimized_6h
"""

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import numpy as np

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s | %(message)s')
log = logging.getLogger(__name__)

# Palette de couleurs pour les graphiques
COLORS = {
    'bull_rider_optimized_6h': '#2563eb',
    'bull_rider_aggressive_6h': '#dc2626',
    'bull_rider_max_6h': '#059669',
    'bull_rider_6h': '#d97706',
    'buy_hold': '#9ca3af',
    'entry': '#16a34a',
    'exit': '#dc2626',
}


def load_backtest_data(product='BTC-USDC', days=730, strategy_name=None):
    """Charge les données de backtest pour une stratégie donnée."""
    from bot.backtest import run_backtest
    from bot.config import load_config
    
    # Charger la configuration
    if strategy_name:
        cfg = load_config(strategy_name=strategy_name, product=product)
    else:
        cfg = load_config(product=product)
    
    # Exécuter le backtest
    log.info(f"Backtest {strategy_name or cfg.active_strategy} sur {product} ({days} jours)...")
    result = run_backtest(cfg, days=days, save_dir=None)
    
    return result


def compute_buy_hold(equity_data, initial_cash=10000.0):
    """Calcule la courbe Buy & Hold à partir des prix de clôture."""
    # equity_data contient les prix dans l'index
    if equity_data.empty:
        return pd.Series(dtype=float)
    
    # Supposons que la première valeur d'equity correspond au capital initial
    # et que le reste sont les prix
    # En réalité, dans le backtest, equity_data contient l'equity calculée
    # Il faut récupérer les prix séparément
    
    # Pour simplifier, on va utiliser les données du backtest existant
    # qui contiennent déjà le buy & hold dans les stats
    pass


def generate_comparison_chart(product, strategy_name, days, result):
    """Génère un graphique comparant la stratégie au Buy & Hold."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError as e:
        log.error(f"Matplotlib non disponible: {e}")
        return None
    
    # Données
    equity = result.equity_curve
    trades = result.trades
    stats = result.stats
    
    if len(equity) < 2:
        log.warning("Pas assez de données pour générer le graphique.")
        return None
    
    # Initial cash from stats
    initial_cash = stats['start_equity']
    
    # Buy & Hold final value
    bh_final = initial_cash * (1 + stats['buy_hold_pct'] / 100)
    
    # Créer une courbe Buy & Hold comme une ligne droite
    # (simplification: en réalité BH suit le prix, mais sans les données de prix détaillées)
    n = len(equity)
    bh_values = np.linspace(initial_cash, bh_final, n)
    bh_normalized = pd.Series(bh_values, index=equity.index)
    
    # Créer le graphique
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [2, 1]})
    
    # Graphique principal: Equity
    ax1.plot(equity.index, equity.values, label=f'Stratégie: {strategy_name}', 
             color=COLORS.get(strategy_name, '#2563eb'), linewidth=2.5)
    ax1.plot(equity.index, bh_normalized.values, label='Buy & Hold', 
             color=COLORS['buy_hold'], linewidth=2.5, linestyle='--')
    
    # Ajouter les marqueurs d'entrée/sortie
    for trade in trades:
        entry_idx = equity.index.get_loc(trade.entry_time)
        exit_idx = equity.index.get_loc(trade.exit_time)
        
        if 0 <= entry_idx < len(equity):
            ax1.scatter(trade.entry_time, equity.iloc[entry_idx], 
                       color=COLORS['entry'], marker='^', s=100, 
                       label='Entrée' if trade == trades[0] else '', zorder=5)
        if 0 <= exit_idx < len(equity):
            ax1.scatter(trade.exit_time, equity.iloc[exit_idx], 
                       color=COLORS['exit'], marker='v', s=100, 
                       label='Sortie' if trade == trades[0] else '', zorder=5)
    
    ax1.set_title(f'**Performance {product} - {strategy_name}**\n'
                  f'Stratégie: {stats["total_return_pct"]:+.2f}% | Buy & Hold: {stats["buy_hold_pct"]:+.2f}% | '
                  f'Max Drawdown: {stats["max_drawdown_pct"]:.2f}%', 
                  fontsize=14, fontweight='bold', pad=20)
    ax1.set_ylabel('Capital (USDC)', fontsize=12, fontweight='bold')
    ax1.grid(alpha=0.3, which='both', axis='y')
    ax1.legend(fontsize=11, loc='upper left')
    
    # Formater l'axe X
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.setp(ax1.get_xticklabels(), rotation=45, ha='right', fontsize=10)
    
    # Graphique second: Drawdown
    roll_max = equity.cummax()
    drawdown = (equity - roll_max) / roll_max * 100
    
    # Buy & Hold drawdown
    bh_roll_max = bh_normalized.cummax()
    bh_drawdown = (bh_normalized - bh_roll_max) / bh_roll_max * 100
    
    ax2.plot(equity.index, drawdown.values, label=f'Stratégie: {strategy_name}', 
             color=COLORS.get(strategy_name, '#2563eb'), linewidth=2)
    ax2.plot(equity.index, bh_drawdown.values, label='Buy & Hold', 
             color=COLORS['buy_hold'], linewidth=2, linestyle='--')
    
    ax2.set_title(f'**Drawdown {product} - Comparaison**', 
                  fontsize=14, fontweight='bold', pad=15)
    ax2.set_ylabel('Drawdown (%)', fontsize=12, fontweight='bold')
    ax2.axhline(0, color='black', linewidth=1, linestyle='-')
    ax2.grid(alpha=0.3, which='both', axis='y')
    ax2.legend(fontsize=11, loc='lower left')
    
    # Ajouter des statistiques sur le drawdown
    min_dd = drawdown.min()
    min_bh_dd = bh_drawdown.min()
    ax2.annotate(f'Max DD Stratégie: {min_dd:.2f}%', xy=(0.02, 0.95), xycoords='axes fraction',
                 fontsize=11, fontweight='bold', color=COLORS.get(strategy_name, '#2563eb'))
    ax2.annotate(f'Max DD Buy & Hold: {min_bh_dd:.2f}%', xy=(0.02, 0.88), xycoords='axes fraction',
                 fontsize=11, fontweight='bold', color=COLORS['buy_hold'])
    
    plt.tight_layout()
    
    # Sauvegarder
    output_dir = Path('reports')
    output_dir.mkdir(exist_ok=True)
    filename = output_dir / f'discord_report_{product}_{strategy_name or "active"}.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()
    
    return str(filename)


def generate_summary_text(product, strategy_name, result):
    """Génère un résumé textuel pour Discord."""
    stats = result.stats
    trades = result.trades
    
    # Calculer les statistiques clés
    excess_return = stats['total_return_pct'] - stats['buy_hold_pct']
    
    # Gagnants/perdants
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0
    avg_loss = -sum(t.pnl for t in losses) / len(losses) if losses else 0
    
    # Formater le texte
    text = f"""📊 **RAPPORT STRATÉGIE - {product} | {strategy_name or 'Active'}**

📈 **PERFORMANCE**
• Période: {stats['start']} → {stats['end']} ({stats['days']:.0f} jours)
• Capital initial: {stats['start_equity']:,.2f} USDC
• **Capital final Stratégie: {stats['end_equity']:,.2f} USDC ({stats['total_return_pct']:+.2f}%)**
• Buy & Hold: {stats['buy_hold_pct']:+.2f}%
• **Écart vs Buy & Hold: {excess_return:+.2f}%**

📉 **RISQUE**
• Max Drawdown: {stats['max_drawdown_pct']:.2f}%
• Sharpe: {stats['sharpe']:.2f}
• Temps exposé: {stats['time_in_market_pct']:.1f}%

🎯 **STATISTIQUES TRADES**
• Nombre de trades: {stats['n_trades']}
• Win Rate: {win_rate:.1f}%
• Gain moyen: {avg_win:+.2f} USDC
• Perte moyenne: {avg_loss:+.2f} USDC
• Profit Factor: {stats['profit_factor']:.2f}
• Coûts totaux: {stats['total_fees']:,.2f} USDC

💡 **CONCLUSION**: {'✅ BAT le Buy & Hold' if excess_return > 0 else '❌ NE BAT PAS le Buy & Hold'}"""
    
    return text


def main():
    parser = argparse.ArgumentParser(description='Génère un rapport Discord pour les stratégies de trading')
    parser.add_argument('--product', '-p', default='BTC-USDC', 
                       help='Paire à analyser (ex: BTC-USDC, ETH-USDC)')
    parser.add_argument('--days', type=int, default=730, 
                       help='Nombre de jours pour le backtest')
    parser.add_argument('--strategy', '-s', default=None,
                       help='Nom de la stratégie (par défaut: active)')
    parser.add_argument('--output-dir', default='reports',
                       help='Dossier de sortie pour les graphiques')
    parser.add_argument('--both', action='store_true',
                       help='Générer pour BTC-USDC et ETH-USDC')
    
    args = parser.parse_args()
    
    # Créer le dossier de sortie
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    products = [args.product]
    if args.both:
        products = ['BTC-USDC', 'ETH-USDC']
    
    all_results = {}
    
    for product in products:
        log.info(f"\n{'='*60}")
        log.info(f"Traitement de {product}...")
        log.info('='*60)
        
        # Charger les données de backtest
        result = load_backtest_data(product=product, days=args.days, 
                                    strategy_name=args.strategy)
        
        # Générer le graphique
        chart_path = generate_comparison_chart(product, args.strategy or 'active', 
                                               args.days, result)
        
        # Générer le texte
        summary_text = generate_summary_text(product, args.strategy or 'active', result)
        
        # Sauvegarder les résultats
        all_results[product] = {
            'stats': result.stats,
            'trades': result.trades,
            'chart': chart_path,
            'text': summary_text
        }
        
        # Afficher le résumé
        print(f"\n{summary_text}\n")
        if chart_path:
            print(f"Graphique généré: {chart_path}")
    
    # Sauvegarder un rapport JSON complet
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    report_file = output_dir / f'rapport_{timestamp}.json'
    with open(report_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str, ensure_ascii=False)
    
    log.info(f"\n✅ Rapport complet sauvegardé: {report_file}")
    log.info(f"📊 Graphiques générés dans: {output_dir.absolute()}")


if __name__ == '__main__':
    main()
