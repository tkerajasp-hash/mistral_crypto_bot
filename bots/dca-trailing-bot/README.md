# DCA Trailing Bot 🎯

> **Bot de Trading avec DCA + Trailing Stop Intelligent**
> *Powered by Mistral Vibe*

---

## 📈 **Stratégie**

Ce bot combine deux concepts puissants :

1. **DCA (Dollar Cost Averaging)** : 
   - 3 entrées échelonnées à **33% du capital** chacune
   - Déclenchées sur des **pullbacks** de -5%, -10%, -15% 
   - **Délai minimum** de 6 bougies (≈ 3 jours en 6H) entre chaque entrée
   
2. **Trailing Stop Intelligent** :
   - **Stop fixe à 10%** sous le plus haut atteint
   - **Ne redescend jamais** (effet cliquet)
   - Protection initiale à 15% pour la première entrée

3. **Take Profit** :
   - **3x le risque** initial (ratio 1:3)
   - Fermeture automatique de la position complète

---

## 🚀 **Utilisation**

### 1. **Installation**

```bash
# Depuis le dossier mistral-vibe-crypto
cd /Users/dev/Documents/crypto/mistral-vibe-crypto/bots/dca-trailing-bot

# Installer les dépendances (si pas déjà fait)
pip install pandas numpy matplotlib requests pyyaml python-dotenv
```

### 2. **Configuration**

#### Configurer Discord (Optionnel)

Pour recevoir les rapports sur Discord :

1. **Créer un Webhook** :
   - Allez sur votre serveur Discord
   - Cliquez sur l'icône ⚙️ (Paramètres du serveur) → **Intégrations** → **Webhooks**
   - Cliquez sur **Nouveau Webhook**
   - Donnez un nom (ex: "DCA Bot")
   - Cliquez sur **Copier le lien du webhook**
   
2. **Configurer dans `config.yaml`** :
   ```yaml
   discord:
     enabled: true
     webhook_url: "VOTRE_WEBHOOK_URL_ICI"
     send_trades: true
     send_daily_report: true
     send_backtest_results: true
   ```

#### Configurer Coinbase (pour Live Trading)

Pour le live trading, vous aurez besoin des clés API Coinbase :

1. Allez sur [Coinbase Advanced Trade Portal](https://portal.cdp.coinbase.com/)
2. Créez une clé API avec permissions **View** et **Trade**
3. Ajoutez dans `.env` :
   ```ini
   COINBASE_API_KEY=votre_clé_api
   COINBASE_API_SECRET=votre_secret_api
   ```

### 3. **Commandes**

```bash
# Vérifier l'accès aux données (public, pas de clé requise)
python -m dca_trailing_bot fetch --days 10

# Vérifier la connexion API Coinbase (nécessite les clés)
python -m dca_trailing_bot account

# Backtest sur 1 an
python -m dca_trailing_bot backtest --days 365

# Backtest sur 1 an avec rapport et graphiques
python -m dca_trailing_bot backtest --days 365 --report

# Backtest sur ETH-USDC
python -m dca_trailing_bot backtest --days 365 -p ETH-USDC --report

# Paper Trading (simulation sur prix réels)
python -m dca_trailing_bot paper --once

# Live Trading (vrais ordres - ATTENTION ⚠️)
python -m dca_trailing_bot live --i-understand-live-trading --once

# Générer un rapport (avec graphiques)
python -m dca_trailing_bot report --days 90

# Voir l'état actuel
python -m dca_trailing_bot status

# Test l'envoi Discord
python -m dca_trailing_bot discord-test
```

---

## 📊 **Exemple de Sortie Backtest**

```
============================================================
         RAPPORT DÉTAILLÉ - DCA TRAILING BOT
============================================================

CONFIGURATION
--------------------------------------
Produit:           BTC-USDC
Granularité:      SIX_HOUR
Capital initial:   $10,000.00

Stratégie:
  - Type:           DCA + Trailing Stop
  - DCA Levels:    3 (33.0% chacun)
  - Pullbacks:     [-5.0, -10.0, -15.0]
  - Trailing:      10%
  - Initial Stop:  15%
  - Take Profit:   3.0x Risk

STATISTIQUES
--------------------------------------
Période:           2023-01-01 -> 2024-01-01 (365 jours)
Capital final:     $14,500.00
Performance:       +45.00%
CAGR:             +22.50%/an
Buy & Hold:       +150.00%
Max Drawdown:     -12.50%
Sharpe Ratio:     1.45

TRADES
--------------------------------------
Total:            15
Complets:          12
Avec DCA:         8
Taux de réussite: 75.0%
Gain moyen:      $+250.00
Perte moyenne:   $-100.00
R moyen:         +1.85
Profit Factor:   2.50
Total DCA:       18
Temps en marché: 35.5%
Coûts totaux:    $125.00

DÉTAILS DES TRADES
--------------------------------------
#    Date        Type      Entrée          Sortie          PnL          R       DCA
----------------------------------------------------------------------
1    2023-01-15 Init      $45,000.00    $48,000.00    +$1,450.00  +1.32    
2    2023-02-01 DCA      $42,500.00    $46,000.00    +$1,250.00  +1.14    L1
3    2023-02-10 DCA      $40,000.00    $44,500.00    +$1,150.00  +1.05    L2
4    2023-03-01 Init      $48,000.00    $45,000.00    -$1,450.00  -1.00    
...
```

---

## 📊 **Graphiques Générés**

Deux graphiques sont générés dans le dossier `reports/` :

### 1. **Graphique des Signaux** (`signals_BTC-USDC_*.png`)
- Affiche le prix
- **Points verts** : Entrées initiales
- **Points bleus** : Entrées DCA (niveau 1, 2, 3)
- **Triangles rouges** : Sorties (stop loss)
- **Triangles violets** : Take profit
- Volume en bas

### 2. **Graphique PnL** (`pnl_BTC-USDC_*.png`)
- **Courbe bleue** : Equity du bot
- **Courbe grise pointillée** : Buy & Hold
- **Courbe rouge pointillée** : Pic d'equity
- **2ème graphe** : Drawdown en %

---

## 🎯 **Paramètres de la Stratégie**

Vous pouvez modifier la stratégie dans `config.yaml` :

### Paramètres DCA
```yaml
strategy:
  dca_levels: 3              # Nombre de niveaux DCA
  dca_percentage: 0.33      # % du capital par niveau
  dca_delay_bars: 6         # Délai entre niveaux (6 bougies = ~3 jours en 6H)
  dca_pullback_levels: [-5.0, -10.0, -15.0]  # Pullbacks en %
```

### Paramètres Trailing Stop
```yaml
strategy:
  trailing_stop_percentage: 10.0   # Trailing stop à 10%
  initial_stop_percentage: 15.0    # Stop initial à 15%
  take_profit_r_multiple: 3.0      # Take profit à 3x le risque
```

### Paramètres de Filtre
```yaml
strategy:
  use_trend_filter: true      # Utiliser le filtre de tendance
  trend_ema: 200              # EMA pour le filtre
  trend_slope_lookback: 20    # Période pour la pente
  adx_period: 14             # Période ADX
  adx_min: 20                # ADX minimum pour trader
```

---

## 💡 **Conseils pour Discord**

### Configuration recommandée :

1. **Créer un canal dédié** : `#dca-bot-reports`
2. **Configurer le webhook** dans ce canal
3. **Activer les notifications** pour ne rien rater

### Format des messages :

- **Backtest** : Embed avec statistiques + 2 images (signaux + PnL)
- **Paper Trading** : Embed avec trading en cours
- **Trades** : Notification instantanée pour chaque entrée/sortie

### Exemple de message Discord :

```
📊 BACKTEST - DCA Trailing Bot
**BTC-USDC** | Période: 2023-01-01 → 2024-01-01

💰 Performance: +45.00% (CAGR: +22.50%/an)
⬇️ Max Drawdown: 12.50%
📈 Trades: 12 complets (75.0% gagnants)
🎯 DCA: 18 entrées DCA
📊 Sharpe: 1.45
💵 Profit Factor: 2.50

[Image: Signaux de Trading]
[Image: Equity Curve & Drawdown]
```

---

## ⚠️ **Avertissements**

1. **Pas de live trading sans test** : Testez toujours en `paper` avant
2. **Risque de perte** : Aucune stratégie n'est infaillible
3. **Backtest ≠ Réel** : Les performances passées ne garantissent pas les résultats futurs
4. **Commissions** : Les frais sont pris en compte dans les calculs
5. **Slippage** : Le slippage est simulé mais peut varier en réel

---

## 📚 **Architecture du Bot**

```
dca-trailing-bot/
├── __main__.py          # CLI principal
├── config.py            # Gestion configuration
├── config.yaml          # Configuration par défaut
├── strategy.py          # Stratégie DCA + Trailing Stop
├── backtest.py          # Moteur de backtest
├── report.py            # Générateur de rapports + graphiques
├── coinbase_client.py   # Client API Coinbase
├── indicators.py        # Indicateurs techniques
├── reports/             # Graphiques générés
├── logs/               # Journaux
├── state/              # État du bot
└── README.md            # Ce fichier
```

---

## 🔧 **Dépannage**

### Problème : "No module named..."
```bash
pip install -r ../../../requirements.txt
```

### Problème : "Config file not found"
```bash
# Vérifiez que vous êtes dans le bon dossier
cd /Users/dev/Documents/crypto/mistral-vibe-crypto/bots/dca-trailing-bot
python -m dca_trailing_bot backtest --days 10
```

### Problème : Discord ne fonctionne pas
```bash
# Vérifiez :
# 1. Webhook URL est correct
# 2. requests est installé (pip install requests)
# 3. Le bot a les permissions d'envoyer des messages
```

---

## 🙏 **Remerciements**

Ce bot a été développé avec **Mistral Vibe** pour améliorer votre stratégie de trading.

- Stratégie originale : **DCA + Trailing Stop**
- Inspiration : Votre idée de combiner DCA et trailing stop
- Optimisation : Trailing stop intelligent + gestion du risque

---

> **⚠️ DISCLAIMER** : Ce bot est à but éducatif et de recherche. Rien ici ne constitue un conseil en investissement. Le trading de cryptomonnaies comporte des risques élevés, y compris la perte totale du capital. Vous êtes seul responsable de vos décisions de trading et de vos résultats.
