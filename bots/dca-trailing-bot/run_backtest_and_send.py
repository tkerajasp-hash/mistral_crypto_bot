#!/usr/bin/env python3
"""
Script prêt à l'emploi : Exécute un backtest et envoie le rapport sur Discord.

Exécutez simplement :
    python3 run_backtest_and_send.py
"""

import sys
from pathlib import Path

# Ajouter le dossier courant au path
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from backtest import run_backtest
from report import generate_report, send_discord_report


def main():
    print("=" * 70)
    print("   🚀 EXÉCUTION BACKTEST + ENVOI DISCORD")
    print("=" * 70)
    
    # Charger la configuration (avec votre webhook Discord)
    print("\n📂 Chargement de la configuration...")
    config = load_config()
    
    print(f"   ✅ Mode: {config.mode}")
    print(f"   ✅ Produit: {config.market.product_id}")
    print(f"   ✅ Discord activé: {config.discord.enabled}")
    if config.discord.webhook_url:
        print(f"   ✅ Webhook: {config.discord.webhook_url[:50]}...")
    else:
        print("   ❌ Webhook non configuré !")
        return
    
    # Exécuter le backtest
    print("\n🔄 Exécution du backtest sur 90 jours...")
    try:
        result = run_backtest(config, days=90, product_id=config.market.product_id)
        print("   ✅ Backtest terminé")
    except Exception as e:
        print(f"   ❌ Erreur backtest: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Afficher le résumé
    print("\n" + "=" * 70)
    print(result.summary())
    print("=" * 70)
    
    # Générer le rapport
    print("\n📊 Génération des graphiques...")
    try:
        report_files = generate_report(result, config, config.market.product_id)
        print(f"   ✅ Rapport généré")
        for file_type, path in report_files.items():
            if path:
                print(f"      - {file_type}: {path}")
    except Exception as e:
        print(f"   ❌ Erreur génération rapport: {e}")
        import traceback
        traceback.print_exc()
    
    # Envoyer sur Discord
    print("\n📤 Envoi sur Discord...")
    try:
        send_discord_report(result, config, config.market.product_id, is_backtest=True)
        print("   ✅ Rapport envoyé sur Discord!")
        print("\n🎉 TERMINÉ ! Vérifiez votre serveur Discord.")
    except Exception as e:
        print(f"   ❌ Erreur envoi Discord: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
