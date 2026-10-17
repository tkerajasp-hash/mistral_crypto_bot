#!/usr/bin/env python3
"""Génère un rapport Discord pour les résultats des backtests.

Ce script :
1. Exécute les backtests pour BTC-USDC et ETH-USDC
2. Génère les graphiques
3. Crée un message Discord formaté avec embeds
4. Envoie le rapport via webhook
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from backtest import run_backtest
from report import ReportGenerator


def format_percentage(value):
    """Formate un nombre en pourcentage avec couleur."""
    if value > 0:
        return f"**+`{value:+.2f}%`**"
    elif value < 0:
        return f"**`{value:+.2f}%`**"
    else:
        return f"`{value:+.2f}%`"


def format_usd(value):
    """Formate un montant en USD."""
    if value > 0:
        return f"**`${value:,.2f}`**"
    elif value < 0:
        return f"**`${value:,.2f}`**"
    else:
        return f"`${value:,.2f}`"


def generate_discord_message(result, product_id):
    """Génère un embed Discord pour un résultat de backtest."""
    stats = result.stats
    
    # Calculer l'écart vs Buy & Hold
    outperformance = stats['total_return_pct'] - stats['buy_hold_pct']
    
    # Couleur de l'embed
    color = 0x2ECC71 if outperformance > 0 else 0xE74C3C
    
    # Description de l'embed
    description = (
        f"**📊 PERFORMANCE {product_id} - 365 jours**\n\n"
        f"**Capital initial:** `${stats['start_equity']:,.2f}`\n"
        f"**Capital final:** {format_usd(stats['end_equity'])}\n"
        f"**Performance:** {format_percentage(stats['total_return_pct'])}\n"
        f"**Buy & Hold:** {format_percentage(stats['buy_hold_pct'])}\n"
        f"**Écart vs B&H:** {format_percentage(outperformance)}\n\n"
        f"**Max Drawdown:** {stats['max_drawdown_pct']:.2f}%\n"
        f"**Sharpe Ratio:** {stats['sharpe']:.2f}\n\n"
        f"**Nombre de trades:** {stats['n_trades']} ({stats['n_dca_trades']} avec DCA)\n"
        f"**Taux de réussite:** {stats['win_rate_pct']:.1f}%\n"
        f"**Profit Factor:** {stats['profit_factor']:.2f}\n"
        f"**Temps en marché:** {stats['time_in_market_pct']:.1f}%\n"
        f"**Total DCA:** {stats['total_dca_entries']}"
    )
    
    # Champs supplémentaires
    fields = [
        {
            "name": "🎯 Meilleur Trade",
            "value": format_usd(stats['max_win']),
            "inline": True
        },
        {
            "name": "❌ Pire Trade",
            "value": format_usd(stats['max_loss']),
            "inline": True
        },
        {
            "name": "📊 CAGR",
            "value": f"{stats['cagr_pct']:+.2f}%",
            "inline": True
        }
    ]
    
    return {
        "title": f"🎯 DCA TRAILING BOT - {product_id}",
        "description": description,
        "color": color,
        "fields": fields,
        "timestamp": None  # Sera ajouté par Discord
    }


def generate_comparison_embed(results):
    """Génère un embed de comparaison entre BTC et ETH."""
    btc_stats = results['BTC-USDC'].stats
    eth_stats = results['ETH-USDC'].stats
    
    # Calculer les écarts
    btc_outperform = btc_stats['total_return_pct'] - btc_stats['buy_hold_pct']
    eth_outperform = eth_stats['total_return_pct'] - eth_stats['buy_hold_pct']
    
    description = (
        "**📊 COMPARAISON BTC vs ETH - 365 jours**\n\n"
        f"**BTC-USDC:** {format_percentage(btc_stats['total_return_pct'])} vs B&H {format_percentage(btc_stats['buy_hold_pct'])} | "
        f"**Écart: {format_percentage(btc_outperform)}**\n\n"
        f"**ETH-USDC:** {format_percentage(eth_stats['total_return_pct'])} vs B&H {format_percentage(eth_stats['buy_hold_pct'])} | "
        f"**Écart: {format_percentage(eth_outperform)}**\n\n"
        "💡 **Analyse:**\n"
    )
    
    if btc_outperform > 0 and eth_outperform > 0:
        description += "✅ Les deux tokens battent le Buy & Hold!\n"
    elif btc_outperform > 0:
        description += "✅ BTC bat le Buy & Hold | ⚠️ ETH à optimiser\n"
    else:
        description += "⚠️ Optimisation nécessaire pour les deux tokens\n"
    
    description += ("\n" + "="*50)
    
    return {
        "title": "🔄 SYNTHÈSE DES PERFORMANCES",
        "description": description,
        "color": 0x3498DB,
        "timestamp": None
    }


def main():
    """Génère les rapports et affiche le message Discord."""
    print("🔄 Génération des rapports...")
    
    # Charger la configuration
    config = load_config('config.yaml')
    
    # Créer le générateur de rapports
    gen = ReportGenerator(output_dir="reports")
    
    # Exécuter les backtests
    products = ['BTC-USDC', 'ETH-USDC']
    results = {}
    files = {}
    
    for product_id in products:
        print(f"  Backtest {product_id}...")
        result = run_backtest(config, days=365, product_id=product_id)
        results[product_id] = result
        files[product_id] = gen.generate(result, config, product_id)
        print(f"    ✅ Rapport généré pour {product_id}")
    
    # Générer les embeds Discord
    print("\n📤 Génération du message Discord...")
    
    embeds = []
    
    # Embed de comparaison
    embeds.append(generate_comparison_embed(results))
    
    # Embeds par token
    for product_id in products:
        embed = generate_discord_message(results[product_id], product_id)
        embeds.append(embed)
    
    # Afficher le message Discord
    print("\n" + "="*60)
    print("COPY THIS FOR DISCORD (with image attachments):")
    print("="*60)
    
    # Message d'introduction
    print("""
🚀 **DCA TRAILING BOT - RAPPORT HEBDOMADAIRE** 🚀

Bonjour @here, voici les résultats des backtests sur 365 jours après les optimisations récentes.

📌 **Objectif:** Battre le Buy & Hold avec une stratégie DCA + Trailing Stop
🎯 **Résultat:** Voir les graphiques et statistiques ci-dessous.

---
    """)
    
    # Afficher chaque embed
    for embed in embeds:
        print(f"\n📊 **{embed['title']}**")
        print("-" * 60)
        print(embed['description'])
        for field in embed.get('fields', []):
            print(f"{field['name']}: {field['value']}")
    
    # Instructions pour les images
    print("\n" + "="*60)
    print("IMAGES À ATTACHER:")
    print("="*60)
    for product_id in products:
        print(f"\n{product_id}:")
        print(f"  📈 Signaux: reports/{Path(files[product_id]['signals']).name}")
        print(f"  💰 PnL: reports/{Path(files[product_id]['pnl']).name}")
    
    print("\n" + "="*60)
    print("COMMENT LES LIR:")
    print("="*60)
    print("""
🔹 **Graphique Signaux (signals_*.png):**
   - 🟢 Points VERTS = Entrées initiales
   - 🟦 Carrés BLEUS = Entrées DCA
   - 🔴 Triangles ROUGES = Sorties par Stop Loss
   - 🟪 Triangles VIOLETS = Sorties par Take Profit

🔹 **Graphique PnL (pnl_*.png):**
   - 🔵 Ligne BLEUE = Capital avec notre stratégie
   - ⚪ Ligne GRISE = Buy & Hold
   - 🔴 Ligne ROUGE pointillée = Pic d'Equity (pour visualiser le drawdown)
   - 📉 Graphe du bas = Drawdown en %

💡 **Interprétation:**
   - Si la ligne BLEUE est AU-DESSUS de la ligne GRISE → On bat le Buy & Hold ✅
   - Plus l'écart est grand, mieux c'est!

---
    """)


if __name__ == "__main__":
    main()
