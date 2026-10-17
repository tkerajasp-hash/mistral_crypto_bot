#!/bin/bash
# Script de lancement du paper trading pour BTC et ETH
# Utilisation: ./LAUNCH_PAPER_TRADING.sh

DIR="/Users/dev/Documents/crypto/python-swing-bot"
VENV=".venv/bin/python"

 echo "🚀 Lancement du Paper Trading pour BTC-USDC et ETH-USDC"
 echo "========================================================"
 echo ""

# Lancer BTC en arrière-plan
echo "🟦 Démarrage BTC-USDC avec bull_rider_optimized_6h..."
cd "$DIR"
$VENV -m bot -p BTC-USDC paper --strategy bull_rider_optimized_6h &
BTC_PID=$!
echo "   ✅ BTC lancé (PID: $BTC_PID)"
echo ""

# Attendre 2 secondes pour éviter les conflits
sleep 2

# Lancer ETH en arrière-plan
echo "🟦 Démarrage ETH-USDC avec bull_rider_6h..."
cd "$DIR"
$VENV -m bot -p ETH-USDC paper --strategy bull_rider_6h &
ETH_PID=$!
echo "   ✅ ETH lancé (PID: $ETH_PID)"
echo ""

echo "========================================================"
echo "✅ Paper Trading en cours !"
echo ""
echo "Pour arrêter:"
echo "   kill $BTC_PID $ETH_PID"
echo ""
echo "Pour vérifier l'état:"
echo "   python -m bot -p BTC-USDC status"
echo "   python -m bot -p ETH-USDC status"
echo ""
echo "Les logs sont dans: $DIR/logs/"
echo "========================================================"

# Attendre que l'utilisateur arrête avec Ctrl+C
wait
