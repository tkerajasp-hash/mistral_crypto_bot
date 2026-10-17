# 🚀 Instructions pour Lancer le Paper Trading

*Stratégies optimisées: BTC-USDC avec `bull_rider_optimized_6h`, ETH-USDC avec `bull_rider_6h`*

---

## 📋 **PRÉREQUIS**

✅ **Stratégies configurées:**
- `bull_rider_optimized_6h` (active pour BTC)
- `bull_rider_6h` (pour ETH)

✅ **Fichiers générés:**
- Graphiques dans `reports/`
- Rapports dans `RAPPORT_DISCORD_FINAL.md` et `DISCORD_SUMMARY.txt`

---

## 🎯 **MÉTHODE 1: LANCER EN CONTINU (PC ALLUMÉ 24/7)**

### Option A: Utiliser le script de lancement
```bash
cd /Users/dev/Documents/crypto/python-swing-bot
./LAUNCH_PAPER_TRADING.sh
```
*Ce script lance BTC et ETH en parallèle dans des processus séparés.*

### Option B: Lancer manuellement dans 2 terminaux

**Terminal 1 (BTC):**
```bash
cd /Users/dev/Documents/crypto/python-swing-bot
.venv/bin/python -m bot -p BTC-USDC paper
```
*Utilise la stratégie active (`bull_rider_optimized_6h`)*

**Terminal 2 (ETH):**
```bash
cd /Users/dev/Documents/crypto/python-swing-bot
.venv/bin/python -m bot -p ETH-USDC paper --strategy bull_rider_6h
```

---

## 🎯 **MÉTHODE 2: LANCER AVEC CRON (PC ÉTEINT ENTRE LES TICKS)**

### 1. Configurer cron
Ouvre ton crontab:
```bash
crontab -e
```

### 2. Ajouter ces lignes
```cron
# BTC - toutes les 6h (granularité SIX_HOUR)
1 */6 * * * cd /Users/dev/Documents/crypto/python-swing-bot && .venv/bin/python -m bot -p BTC-USDC paper --once --strategy bull_rider_optimized_6h >> logs/cron_BTC.log 2>&1

# ETH - toutes les 6h (décalé de 2h)
3 */6 * * * cd /Users/dev/Documents/crypto/python-swing-bot && .venv/bin/python -m bot -p ETH-USDC paper --once --strategy bull_rider_6h >> logs/cron_ETH.log 2>&1

# Générer les rapports quotidiens à 8h
0 8 * * * cd /Users/dev/Documents/crypto/python-swing-bot && .venv/bin/python generate_discord_report.py --product BTC-USDC --strategy bull_rider_optimized_6h >> logs/cron_report_BTC.log 2>&1
0 8 * * * cd /Users/dev/Documents/crypto/python-swing-bot && .venv/bin/python generate_discord_report.py --product ETH-USDC --strategy bull_rider_6h >> logs/cron_report_ETH.log 2>&1
```

### 3. Sauvegarder et quitter
- Appuie sur `Ctrl+O` puis `Entrée` pour sauvegarder
- Appuie sur `Ctrl+X` pour quitter

### 4. Vérifier que cron est actif
```bash
crontab -l
```

---

## 📊 **VÉRIFIER QUE TOUT FONCTIONNE**

### 1. Vérifier l'état du bot
```bash
# Pour BTC
python -m bot -p BTC-USDC status

# Pour ETH
python -m bot -p ETH-USDC status
```

### 2. Voir les logs
```bash
# Logs BTC
tail -f logs/cron_BTC.log

# Logs ETH
tail -f logs/cron_ETH.log
```

### 3. Voir l'historique des trades
```bash
# Trades BTC
cat logs/trades_BTC-USDC.csv

# Trades ETH
cat logs/trades_ETH-USDC.csv
```

### 4. Voir la courbe d'equity
```bash
# Equity BTC
cat logs/equity_BTC-USDC.csv

# Equity ETH
cat logs/equity_ETH-USDC.csv
```

---

## ⏹️ **ARRÊTER LE PAPER TRADING**

### Si lancé avec le script
```bash
# Trouver les PIDs
ps aux | grep "python -m bot"

# Tuer les processus (remplacer XXXX par les PIDs)
kill XXXX XXXX
```

### Si lancé avec cron
```bash
# Ébeiter cron
crontab -e
# Supprimer les lignes du paper trading
# Sauvegarder et quitter
```

---

## 💡 **COMMANDES UTILES**

| Commande | Description |
|----------|-------------|
| `python -m bot -p BTC-USDC paper` | Lancer paper trading BTC |
| `python -m bot -p ETH-USDC paper --strategy bull_rider_6h` | Lancer paper trading ETH |
| `python -m bot -p BTC-USDC status` | Voir l'état BTC |
| `python -m bot -p ETH-USDC status` | Voir l'état ETH |
| `python -m bot -p BTC-USDC backtest --days 30` | Backtest rapide |
| `python generate_discord_report.py --product BTC-USDC` | Générer rapport |

---

## 📈 **QUE VA FAIRE LE BOT ?**

### BTC-USDC (`bull_rider_optimized_6h`)
- **Entrée:** Sur cassure Donchian OU repli sur EMA20
- **Sortie:** Sur cassure Donchian basse OU stop loss coupé
- **Position:** 4% de risque par trade, trailing stop à 3.5x ATR
- **Objectif:** Capturer les tendances haussières de BTC

### ETH-USDC (`bull_rider_6h`)
- **Entrée:** Sur cassure Donchian OU repli sur EMA20
- **Sortie:** Sur cassure Donchian basse OU stop loss coupé
- **Position:** 0.75% de risque par trade, trailing stop à 4x ATR
- **Objectif:** Stratégie prudente pour ETH (marché baissier)

---

## ⚠️ **IMPORTANT**

1. **PC allumé:** OUI, nécessaire pour le trading en temps réel
   - **Sauf** si tu utilises cron avec `--once`

2. **Capital virtuel:** 10,000 USDC par défaut (modifiable dans `config.yaml`)

3. **Pas d'ordres réels:** Le mode `paper` ne passe **aucune ordre réel**

4. **Pour passer en live:**
   - Changer `mode: paper` à `mode: live` dans `config.yaml`
   - Ajouter `--i-understand-live-trading` à la commande
   - **Ne fais ça que quand tu es prêt !**

---

## 🎉 **C'EST PRÊT !**

Tu peux maintenant lancer le paper trading avec la méthode qui te convient.

**Recommandation:** Commence avec la **Méthode 2 (cron)** si tu ne veux pas garder ton PC allumé.

Si tu as des questions, demande-moi !
