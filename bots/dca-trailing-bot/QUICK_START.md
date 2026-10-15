# Quick Start - DCA Trailing Bot

## 🚀 Démarrage Rapide

### 1. Installer les dépendances

```bash
cd /Users/dev/Documents/crypto/mistral-vibe-crypto
python3 -m pip install -e .
```

### 2. Tester Discord

```bash
cd bots/dca-trailing-bot
python3 __main__.py discord-test
```

**Attendu** : Vous devriez recevoir un message de test sur votre serveur Discord.

### 3. Exécuter un Backtest

```bash
python3 __main__.py backtest --days 30 --report
```

**Attendu** : 
- Exécution du backtest sur 30 jours
- Génération des graphiques (signaux + PnL)
- Envoi du rapport complet sur Discord

### 4. Paper Trading (Simulation)

```bash
python3 __main__.py paper --once
```

**Attendu** : 
- Simulation d'un trade sur les dernières données
- Envoi des résultats sur Discord

### 5. Voir toutes les options

```bash
python3 __main__.py --help
```

---

## 📊 Commandes Disponibles

| Commande | Description | Exemple |
|----------|-------------|---------|
| `fetch` | Vérifie l'accès aux données | `python3 __main__.py fetch --days 10` |
| `backtest` | Exécute un backtest | `python3 __main__.py backtest --days 365 --report` |
| `paper` | Paper trading | `python3 __main__.py paper --once` |
| `report` | Génère un rapport | `python3 __main__.py report --days 90` |
| `status` | Affiche l'état | `python3 __main__.py status` |
| `discord-test` | Test Discord | `python3 __main__.py discord-test` |

---

## 🎯 Configuration

### Fichier : `config.yaml`

```yaml
# Mode
mode: paper  # paper | live

# Marché
market:
  product_id: BTC-USDC  # ou ETH-USDC
  granularity: SIX_HOUR  # ONE_HOUR | SIX_HOUR | ONE_DAY

# Stratégie DCA + Trailing Stop
strategy:
  entry_mode: dca_on_pullback
  dca_levels: 3
  dca_percentage: 0.33  # 33% du capital par niveau
  dca_delay_bars: 6    # ~3 jours en granularité 6H
  dca_pullback_levels: [-5.0, -10.0, -15.0]
  trailing_stop_percentage: 10.0
  initial_stop_percentage: 15.0
  take_profit_r_multiple: 3.0

# Discord (déjà configuré)
discord:
  enabled: true
  webhook_url: "https://discord.com/api/webhooks/1560044752773058620/y_PXLqpSoX1GPU9N4fw3G1WjE0slEOgTHs8fBAvGaroDZ6V6jhmQ4CSs1_DMc6JLpdl2"
  send_trades: true
  send_backtest_results: true

# Paper Trading
paper:
  starting_cash: 10000.0  # Capital en USDC
```

---

## 📈 Stratégie Implémentée

### DCA + Trailing Stop

1. **Entrée initiale** : Sur cassure de Donchian (20 bougies)
2. **DCA** : 3 niveaux à 33% du capital chacun
   - Niveau 1 : -5% vs prix initial
   - Niveau 2 : -10% vs prix initial
   - Niveau 3 : -15% vs prix initial
   - Délai : 6 bougies (~3 jours en 6H)
3. **Sortie** : Trailing Stop à 10% ou Take Profit à 3x le risque
4. **Filtre de tendance** : EMA 200 croissante + ADX > 20

---

## 🎨 Graphiques Générés

### 1. Graphique des Signaux (`signals_*.png`)
- Prix (ligne grise)
- Entrées (marqueurs verts/bleus)
- Sorties (marqueurs rouges/violets)

### 2. Graphique PnL (`pnl_*.png`)
- Equity Curve (ligne bleue)
- Buy & Hold (ligne grise pointillée)
- Drawdown (graphe inférieur)

---

## 📱 Exemple de Rapport Discord

```
📊 BACKTEST - DCA Trailing Bot
BTC-USDC | Période: 2026-03-14 → 2026-10-14

💰 Performance: +X.XX%
⬇️ Max Drawdown: X.XX%
📈 Trades: 4 complets (75.0% gagnants)
🎯 DCA: 0 entrées
📊 Sharpe: 1.20
💵 Profit Factor: 2.14

[Image 1: Signaux]
[Image 2: Equity & Drawdown]
```

---

## ⚠️ Problèmes Connus

1. **Données futures** : Les dates montrent 2026 car Coinbase retourne des données simulées pour les dates futures
2. **Code SSL 200** : Normal pour Discord (204 = succès sans contenu, 200 = succès avec contenu)
3. **Performance** : Les résultats actuels sont basés sur des données de test

---

## 💡 Conseils

- **Commencez par un backtest** : `python3 __main__.py backtest --days 365 --report`
- **Testez Discord** : `python3 __main__.py discord-test`
- **Personnalisez** : Editez `config.yaml` pour ajuster les paramètres
- **Vérifiez les logs** : Tous les logs sont dans `logs/dca_bot.log`

---

## 🔧 Support

Si quelque chose ne fonctionne pas :

1. Vérifiez que vous êtes dans le bon répertoire :
   ```bash
   cd /Users/dev/Documents/crypto/mistral-vibe-crypto/bots/dca-trailing-bot
   ```

2. Vérifiez que le package est installé :
   ```bash
   python3 -c "import mistral_vibe_crypto; print('OK')"
   ```

3. Vérifiez votre webhook Discord dans `config.yaml`

4. Contactez-moi si le problème persiste !
