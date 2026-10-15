"""Générateur de rapports pour le DCA Trailing Bot.

Génère :
1. Un graphe avec les signaux (entrées/sorties)
2. Un graphe avec le PnL cumulé
3. Un rapport textuel détaillé
"""

from __future__ import annotations

import io
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Ajouter le dossier courant au path
sys.path.insert(0, str(Path(__file__).parent))

import matplotlib
matplotlib.use("Agg")  # Mode non-interactif pour sauvegarde
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

from backtest import BacktestResult, Trade
from config import BotConfig


# Couleurs pour les graphiques
COLORS = {
    "entry": "#2ECC71",      # Vert (entrée)
    "dca": "#3498DB",        # Bleu (DCA)
    "exit": "#E74C3C",       # Rouge (sortie)
    "take_profit": "#9B59B6", # Violet (take profit)
    "stop_loss": "#E67E22",   # Orange (stop loss)
    "profit": "#2ECC71",      # Vert (PNL positif)
    "loss": "#E74C3C",        # Rouge (PNL négatif)
    "equity": "#3498DB",      # Bleu (equity)
    "bh": "#95A5A6",         # Gris (buy & hold)
}


class ReportGenerator:
    """Génère des rapports avec graphiques."""
    
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    # ------------------------------------------------------------------
    def generate(
        self,
        result: BacktestResult,
        config: BotConfig,
        product_id: str,
    ) -> dict:
        """Génère un rapport complet.
        
        Returns:
            dict avec les paths des fichiers générés
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Générer le graphe des signaux
        signals_path = self._generate_signals_chart(result, product_id, timestamp)
        
        # 2. Générer le graphe du PnL
        pnl_path = self._generate_pnl_chart(result, product_id, timestamp)
        
        # 3. Générer le rapport textuel
        report_path = self._generate_text_report(result, config, product_id, timestamp)
        
        return {
            "signals": signals_path,
            "pnl": pnl_path,
            "report": report_path,
        }
    
    # ------------------------------------------------------------------
    def _generate_signals_chart(
        self,
        result: BacktestResult,
        product_id: str,
        timestamp: str,
    ) -> str:
        """Génère un graphe avec les signaux d'entrée/sortie."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})
        
        # Récupérer les données
        data = self._get_price_data(result)
        if data is None or len(data) == 0:
            return ""
        
        # Tracer le prix
        ax1.plot(data.index, data["close"], color="#7F8C8D", alpha=0.5, label="Prix (USDC)")
        
        # Ajouter un titre explicatif
        ax1.set_title(
            f"Stratégie DCA + Trailing Stop - {product_id}\n"
            f"📌 Entrées : Vert (Init) / Bleu (DCA) | Sorties : Rouge (Stop) / Violet (Take Profit)\n"
            f"📊 Logique : Entre → Ajoute DCA à -5%, -10%, -15% → Trailing Stop 10% sous le plus haut",
            fontsize=12, fontweight='bold', pad=20
        )
        
        # Tracer les signaux
        for trade in result.trades:
            if trade.entry_time:
                # Entrée
                color = COLORS["dca"] if trade.is_dca or trade.dca_level > 0 else COLORS["entry"]
                marker = "o" if trade.dca_level == 0 else "s"
                ax1.scatter(
                    trade.entry_time, trade.entry_price,
                    color=color, marker=marker, s=100, zorder=5,
                    label=f"Entrée{' DCA' if trade.is_dca else ''} L{trade.dca_level}"
                )
            
            if trade.exit_time:
                # Sortie
                color = COLORS["take_profit"] if "TAKE PROFIT" in trade.reason else COLORS["stop_loss"]
                marker = "^"
                ax1.scatter(
                    trade.exit_time, trade.exit_price,
                    color=color, marker=marker, s=100, zorder=5,
                    label=f"Sortie: {trade.reason[:20]}"
                )
        
        # Légende et labels
        ax1.set_title(f"Signaux de Trading - {product_id}", fontsize=14, fontweight='bold')
        ax1.set_ylabel("Prix (USDC)")
        ax1.grid(True, alpha=0.3)
        
        # Formater l'axe des dates
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax1.get_xticklabels(), rotation=45, ha='right')
        
        # Légende unique (éviter les doublons)
        handles, labels = ax1.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax1.legend(by_label.values(), by_label.keys(), loc='upper left')
        
        # 2ème graphe: Volume (si disponible)
        if "volume" in data.columns:
            ax2.bar(data.index, data["volume"], color="#95A5A6", alpha=0.6)
            ax2.set_ylabel("Volume")
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')
        else:
            ax2.axis('off')
        
        # Sauvegarder
        filename = f"signals_{product_id}_{timestamp}.png"
        filepath = self.output_dir / filename
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
    
    # ------------------------------------------------------------------
    def _generate_pnl_chart(
        self,
        result: BacktestResult,
        product_id: str,
        timestamp: str,
    ) -> str:
        """Génère un graphe avec le PnL cumulé."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [2, 1]})
        
        # Ajouter un titre explicatif
        ax1.set_title(
            f"Performance Financière - {product_id}\n"
            f"📈 Ligne Bleue = Capital avec stratégie | Ligne Grise = Buy & Hold\n"
            f"⬇️  Graphe du bas = Drawdown (pourcentage de perte par rapport au pic)",
            fontsize=12, fontweight='bold', pad=20
        )
        
        # Graphe 1: Equity Curve
        equity = result.equity_curve
        if len(equity) > 0:
            ax1.plot(equity.index, equity, color=COLORS["equity"], linewidth=2, label="Equity (Stratégie)")
            
            # Tracer Buy & Hold
            data = self._get_price_data(result)
            if data is not None and len(data) > 0:
                bh_start = float(data.iloc[0]["close"])
                bh = data["close"] / bh_start * result.stats.get("start_equity", 10000)
                ax1.plot(data.index, bh, color=COLORS["bh"], linestyle="--", linewidth=1.5, label="Buy & Hold")
            
            # Tracer le pic
            peak = equity.cummax()
            ax1.plot(equity.index, peak, color="#E74C3C", linestyle=":", linewidth=1, label="Pic Equity")
            
            ax1.set_title(f"Equity Curve - {product_id}", fontsize=14, fontweight='bold')
            ax1.set_ylabel("Capital (USDC)")
            ax1.grid(True, alpha=0.3)
            ax1.legend(loc='upper left')
        
        # Graphe 2: Drawdown
        if len(equity) > 0:
            roll_max = equity.cummax()
            drawdown = (equity - roll_max) / roll_max * 100
            ax2.plot(equity.index, drawdown, color=COLORS["loss"], linewidth=1.5, label="Drawdown %")
            ax2.axhline(0, color="black", linestyle="-", linewidth=0.5)
            ax2.set_ylabel("Drawdown (%)")
            ax2.grid(True, alpha=0.3)
            ax2.legend(loc='upper right')
        
        # Formater les axes
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        
        # Sauvegarder
        filename = f"pnl_{product_id}_{timestamp}.png"
        filepath = self.output_dir / filename
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
    
    # ------------------------------------------------------------------
    def _generate_text_report(
        self,
        result: BacktestResult,
        config: BotConfig,
        product_id: str,
        timestamp: str,
    ) -> str:
        """Génère un rapport textuel détaillé."""
        filename = f"report_{product_id}_{timestamp}.txt"
        filepath = self.output_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("         RAPPORT DÉTAILLÉ - DCA TRAILING BOT\n")
            f.write("=" * 70 + "\n\n")
            
            # Configuration
            f.write("CONFIGURATION\n")
            f.write("-" * 70 + "\n")
            f.write(f"Produit:           {product_id}\n")
            f.write(f"Granularité:      {config.market.granularity}\n")
            f.write(f"Capital initial:   ${config.paper.starting_cash:,.2f}\n")
            f.write(f"\nStratégie:\n")
            f.write(f"  - Type:           DCA + Trailing Stop\n")
            f.write(f"  - DCA Levels:    {config.strategy.dca_levels} ({config.strategy.dca_percentage*100}% chacun)\n")
            f.write(f"  - Pullbacks:     {config.strategy.dca_pullback_levels}\n")
            f.write(f"  - Trailing:      {config.strategy.trailing_stop_percentage}%\n")
            f.write(f"  - Initial Stop:  {config.strategy.initial_stop_percentage}%\n")
            f.write(f"  - Take Profit:   {config.strategy.take_profit_r_multiple}x Risk\n")
            f.write("\n")
            
            # Statistiques
            f.write("STATISTIQUES\n")
            f.write("-" * 70 + "\n")
            stats = result.stats
            f.write(f"Période:           {stats.get('start', '?')} -> {stats.get('end', '?')} ({stats.get('days', 0):.0f} jours)\n")
            f.write(f"Capital final:     ${stats.get('end_equity', 0):,.2f}\n")
            f.write(f"Performance:       {stats.get('total_return_pct', 0):+,.2f}%\n")
            f.write(f"CAGR:             {stats.get('cagr_pct', 0):+,.2f}%/an\n")
            f.write(f"Buy & Hold:       {stats.get('buy_hold_pct', 0):+,.2f}%\n")
            f.write(f"Max Drawdown:     {stats.get('max_drawdown_pct', 0):.2f}%\n")
            f.write(f"Sharpe Ratio:     {stats.get('sharpe', 0):.2f}\n")
            f.write("\n")
            
            # Trades
            f.write("TRADES\n")
            f.write("-" * 70 + "\n")
            f.write(f"Total:            {stats.get('n_trades', 0)}\n")
            f.write(f"Complets:          {stats.get('n_complete_trades', 0)}\n")
            f.write(f"Avec DCA:         {stats.get('n_dca_trades', 0)}\n")
            f.write(f"Taux de réussite: {stats.get('win_rate_pct', 0):.1f}%\n")
            f.write(f"Gain moyen:      ${stats.get('avg_win', 0):+,.2f}\n")
            f.write(f"Perte moyenne:   ${stats.get('avg_loss', 0):+,.2f}\n")
            f.write(f"R moyen:         {stats.get('avg_r', 0):+,.2f}\n")
            f.write(f"Profit Factor:   {stats.get('profit_factor', 0):.2f}\n")
            f.write(f"Total DCA:       {stats.get('total_dca_entries', 0)}\n")
            f.write(f"Temps en marché: {stats.get('time_in_market_pct', 0):.1f}%\n")
            f.write(f"Coûts totaux:    ${stats.get('total_fees', 0):,.2f}\n")
            f.write("\n")
            
            # Détails des trades
            f.write("DÉTAILS DES TRADES\n")
            f.write("-" * 70 + "\n")
            f.write(f"{'#':<4} {'Date':<12} {'Type':<10} {'Entrée':<12} {'Sortie':<12} {'PnL':<12} {'R':<8} {'DCA'}\n")
            f.write("-" * 70 + "\n")
            
            for i, trade in enumerate(result.trades):
                dca_marker = f"L{trade.dca_level}" if trade.dca_level > 0 or trade.is_dca else ""
                trade_type = "DCA" if trade.is_dca else "Init"
                entry_date = trade.entry_time.strftime("%Y-%m-%d") if trade.entry_time else "?"
                exit_date = trade.exit_time.strftime("%Y-%m-%d") if trade.exit_time else "?"
                entry_price = f"${trade.entry_price:,.2f}" if trade.entry_price else "?"
                exit_price = f"${trade.exit_price:,.2f}" if trade.exit_price else "?"
                pnl = f"${trade.pnl:+,.2f}" if not pd.isna(trade.pnl) else "?"
                r = f"{trade.r_multiple:+.2f}" if trade.r_multiple else "?"
                
                f.write(f"{i+1:<4} {entry_date:<12} {trade_type:<10} {entry_price:<12} {exit_price:<12} {pnl:<12} {r:<8} {dca_marker}\n")
        
        return str(filepath)
    
    # ------------------------------------------------------------------
    def _get_price_data(self, result: BacktestResult) -> Optional[pd.DataFrame]:
        """Récupère les données de prix depuis le backtest."""
        return result.price_data


# ------------------------------------------------------------------
# Fonctions utilitaires
# ------------------------------------------------------------------

def generate_report(
    result: BacktestResult,
    config: BotConfig,
    product_id: str,
    output_dir: str = "reports",
) -> dict:
    """Génère un rapport complet.
    
    Returns:
        dict avec les paths des fichiers générés
    """
    generator = ReportGenerator(output_dir)
    return generator.generate(result, config, product_id)


def generate_image_report(
    result: BacktestResult,
    config: BotConfig,
    product_id: str,
    output_dir: str = "reports",
) -> dict:
    """Génère un rapport avec images uniquement (pour Discord).
    
    Returns:
        dict avec les paths des images
    """
    generator = ReportGenerator(output_dir)
    return {
        "signals": generator._generate_signals_chart(result, product_id, "discord"),
        "pnl": generator._generate_pnl_chart(result, product_id, "discord"),
    }


# ------------------------------------------------------------------
# Discord Integration
# ------------------------------------------------------------------

def send_discord_report(
    result: BacktestResult,
    config: BotConfig,
    product_id: str,
    is_backtest: bool = True,
) -> None:
    """Envoie le rapport sur Discord."""
    webhook_url = config.discord.webhook_url
    if not webhook_url:
        print("❌ Webhook Discord non configuré")
        return
    
    try:
        import requests
        import json
        from datetime import datetime
        
        # Générer les images
        images = generate_image_report(result, config, product_id)
        
        # Préparer le message
        stats = result.stats
        
        # Embed principal
        embed = {
            "title": f"📊 {'BACKTEST' if is_backtest else 'PAPER TRADING'} - DCA Trailing Bot",
            "description": f"**{product_id}** | Période: {stats.get('start', '?')} → {stats.get('end', '?')}",
            "color": 0x2ECC71 if stats.get('total_return_pct', 0) > 0 else 0xE74C3C,
            "fields": [
                {
                    "name": "💰 Performance",
                    "value": f"{stats.get('total_return_pct', 0):+,.2f}% (CAGR: {stats.get('cagr_pct', 0):+,.2f}%/an)",
                    "inline": True
                },
                {
                    "name": "⬇️ Max Drawdown",
                    "value": f"{stats.get('max_drawdown_pct', 0):.2f}%",
                    "inline": True
                },
                {
                    "name": "📈 Trades",
                    "value": f"{stats.get('n_complete_trades', 0)} complets ({stats.get('win_rate_pct', 0):.1f}% gagnants)",
                    "inline": True
                },
                {
                    "name": "🎯 DCA",
                    "value": f"{stats.get('total_dca_entries', 0)} entrées DCA",
                    "inline": True
                },
                {
                    "name": "📊 Sharpe",
                    "value": f"{stats.get('sharpe', 0):.2f}",
                    "inline": True
                },
                {
                    "name": "💵 Profit Factor",
                    "value": f"{stats.get('profit_factor', 0):.2f}",
                    "inline": True
                },
            ],
            "timestamp": datetime.now().isoformat(),
            "footer": {
                "text": "DCA Trailing Bot - Mistral Vibe Crypto"
            }
        }
        
        # Message principal
        payload = {
            "embeds": [embed]
        }
        
        # Envoyer le message
        response = requests.post(webhook_url, json=payload)
        
        if response.status_code != 204:
            print(f"❌ Erreur Discord: {response.status_code} - {response.text}")
            return
        
        # Envoyer les images
        for image_type, path in images.items():
            if path and os.path.exists(path):
                try:
                    with open(path, "rb") as f:
                        files = {"file": (os.path.basename(path), f, "image/png")}
                        payload = {
                            "content": f"📈 **{image_type.upper()}** - {product_id}",
                        }
                        response = requests.post(webhook_url, files=files, data=payload)
                        if response.status_code == 204:
                            print(f"   ✅ Image {image_type} envoyée")
                        else:
                            print(f"   ⚠️  Image {image_type}: code {response.status_code}")
                except Exception as e:
                    print(f"   ⚠️  Erreur image {image_type}: {e}")
        
        print("✅ Rapport envoyé sur Discord avec succès")
        
    except ImportError:
        print("❌ requests non installé - installez avec: pip install requests")
    except Exception as e:
        print(f"❌ Erreur: {e}")
