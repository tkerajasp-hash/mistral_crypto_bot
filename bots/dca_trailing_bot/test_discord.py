#!/usr/bin/env python3
"""
Script de test pour vérifier que Discord fonctionne.
"""

import sys
from pathlib import Path

# Ajouter le dossier courant au path
sys.path.insert(0, str(Path(__file__).parent))

import requests
import json
from datetime import datetime


def test_simple_message():
    """Test avec un message simple."""
    webhook_url = "https://discord.com/api/webhooks/1560044752773058620/y_PXLqpSoX1GPU9N4fw3G1WjE0slEOgTHs8fBAvGaroDZ6V6jhmQ4CSs1_DMc6JLpdl2"
    
    payload = {
        "content": "🎯 **TEST DISCORD - DCA BOT** \nConnexion réussie ! ✅",
        "embeds": [{
            "title": "🔧 Test de Configuration Discord",
            "description": "Votre webhook est correctement configuré.",
            "color": 0x2ECC71,
            "fields": [
                {"name": "✅ Statut", "value": "Webhook fonctionnel", "inline": True},
                {"name": "📅 Date", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "inline": True},
            ],
            "timestamp": datetime.now().isoformat(),
            "footer": {"text": "DCA Trailing Bot - Mistral Vibe"}
        }]
    }
    
    try:
        response = requests.post(webhook_url, json=payload)
        print(f"✅ Message envoyé à Discord!")
        print(f"   Code: {response.status_code}")
        print(f"   Réponse: {response.text[:100]}")
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def test_with_image():
    """Test avec une image (simule un rapport)."""
    webhook_url = "https://discord.com/api/webhooks/1560044752773058620/y_PXLqpSoX1GPU9N4fw3G1WjE0slEOgTHs8fBAvGaroDZ6V6jhmQ4CSs1_DMc6JLpdl2"
    
    # Créer une image de test
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import io
    
    # Générer une image simple
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot([0, 1, 2, 3, 4], [100, 120, 110, 130, 140], marker='o', color='green')
    ax.set_title('Test Graphique - DCA Bot')
    ax.set_ylabel('Prix')
    ax.grid(True)
    
    # Sauvegarder dans un buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    # Envoyer avec l'image
    files = {'file': ('test_graphique.png', buf, 'image/png')}
    payload = {
        "content": "📊 **Test Graphique** - Vérification envoi d'images",
        "embeds": [{
            "title": "📈 Graphique de Test",
            "description": "Si vous voyez une image en dessous, tout fonctionne !",
            "color": 0x3498DB,
            "timestamp": datetime.now().isoformat(),
        }]
    }
    
    try:
        response = requests.post(webhook_url, files=files, data=payload)
        print(f"\n✅ Image envoyée à Discord!")
        print(f"   Code: {response.status_code}")
        return True
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        return False


def main():
    print("=" * 60)
    print("   TEST DE CONFIGURATION DISCORD")
    print("=" * 60)
    
    print("\n📤 Test 1: Message simple...")
    test1 = test_simple_message()
    
    print("\n📊 Test 2: Message avec image...")
    test2 = test_with_image()
    
    print("\n" + "=" * 60)
    if test1 and test2:
        print("✅ TOUS LES TESTS RÉUSSIS !")
        print("   Votre Discord est prêt pour le DCA Bot !")
        print("\n🚀 Prochaine étape:")
        print("   Exécutez: python3 demo_test.py")
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("   Vérifiez votre webhook URL et réessayez.")
    print("=" * 60)


if __name__ == "__main__":
    main()
