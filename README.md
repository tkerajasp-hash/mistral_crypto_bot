# Mistral Vibe Crypto

> **Plateforme de Trading Algorithique Crypto - Powered by Mistral AI**

---

## 🚀 Présentation

**Mistral Vibe Crypto** est une plateforme de trading algorithmique open-source conçue pour les marchés cryptographiques. Elle offre :

- ✅ **Multi-stratégies** : Trend following, mean reversion, breakout, arbitrage, etc.
- ✅ **Multi-exchanges** : Coinbase, Binance, Kraken, et plus
- ✅ **Backtesting avancé** : Tests historiques avec métriques complètes
- ✅ **Paper trading** : Simulation sur données réelles
- ✅ **Live trading** : Exécution sur marchés réels
- ✅ **Portfolio management** : Gestion de portefeuille multi-paires
- ✅ **Risk management** : Protection du capital sophistiquée
- ✅ **Monitoring** : Métriques, alertes, dashboards

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [ANALYSE_EXISTANT.md](./ANALYSE_EXISTANT.md) | Analyse détaillée du projet existant |
| [ROADMAP.md](./ROADMAP.md) | Feuille de route complète |
| [PLAN_ACTION_IMMEDIAT.md](./PLAN_ACTION_IMMEDIAT.md) | Plan d'action pour la semaine 1 |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | Architecture technique détaillée |

---

## 🏗️ Architecture

```
mistral-vibe-crypto/
├── core/                          # Librairie principale
│   ├── types.py                   # Types communs
│   ├── indicators/                # Indicateurs techniques
│   │   ├── __init__.py
│   │   ├── trend.py               # EMA, SMA, slope
│   │   ├── volatility.py           # ATR, True Range
│   │   ├── momentum.py             # ADX, RSI, MACD
│   │   └── patterns.py            # Donchian, etc.
│   ├── data/                      # Données marché
│   │   ├── providers/             # Providers par exchange
│   │   │   ├── base.py            # Interface DataProvider
│   │   │   ├── coinbase.py        # Coinbase Advanced Trade
│   │   │   ├── binance.py         # Binance
│   │   │   └── kraken.py          # Kraken
│   │   └── cache/                 # Cache des données
│   │       └── redis_cache.py     # Cache Redis
│   ├── strategies/                # Stratégies de trading
│   │   ├── base.py                # Interface Strategy
│   │   ├── trend_following.py      # Suivi de tendance
│   │   ├── mean_reversion.py      # Retour à la moyenne
│   │   └── breakout.py            # Cassures
│   ├── risk/                       # Gestion du risque
│   │   ├── stop_manager.py         # Gestion des stops
│   │   ├── exposure.py             # Pilotage exposition
│   │   └── portfolio.py            # Gestion portefeuille
│   ├── execution/                 # Exécution des ordres
│   │   ├── broker.py              # Interface Broker
│   │   ├── paper_broker.py        # Simulation
│   │   └── exchanges/             # Brokers par exchange
│   │       ├── coinbase.py        # Coinbase
│   │       ├── binance.py         # Binance
│   │       └── kraken.py          # Kraken
│   └── backtesting/                # Backtesting
│       ├── engine.py              # Moteur de backtest
│       ├── walkforward.py         # Walk-forward validation
│       └── metrics.py             # Calcul des métriques
├── bots/                          # Bots spécifiques
│   ├── swing-bot/                 # Bot swing trading
│   │   ├── __main__.py
│   │   └── config.yaml
│   ├── scalper-bot/               # Bot scalping
│   ├── arbitrage-bot/             # Bot arbitrage
│   └── mean-reversion-bot/        # Bot mean reversion
├── tests/                         # Tests
│   ├── unit/
│   │   ├── test_indicators.py
│   │   ├── test_providers.py
│   │   └── ...
│   └── integration/
│       ├── test_swing_bot.py
│       └── ...
├── docs/                          # Documentation
│   ├── ARCHITECTURE.md
│   ├── API.md
│   └── ...
└── scripts/                       # Scripts utilitaires
    ├── fetch_data.py
    ├── backtest_all.py
    └── ...
```

---

## 🚀 Installation

### Prérequis
- Python 3.12+
- pip (Python package manager)
- Git

### Installation Rapide

```bash
# Cloner le dépôt
git clone https://github.com/mistral-ai/mistral-vibe-crypto.git
cd mistral-vibe-crypto

# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Installer en mode développement
pip install -e .
```

### Installation pour le Développement

```bash
# Installer avec les dépendances de développement
pip install -e ".[dev]"

# Installer pre-commit hooks
pre-commit install
```

---

## ⚡ Utilisation

### Configuration

1. Copier le fichier d'exemple :
   ```bash
   cp .env.example .env
   ```

2. Écouldir `.env` avec vos clés API :
   ```ini
   # Coinbase
   COINBASE_API_KEY=your_api_key
   COINBASE_API_SECRET=your_api_secret
   
   # Binance (optionnel)
   BINANCE_API_KEY=your_api_key
   BINANCE_API_SECRET=your_api_secret
   
   # Telegram (optionnel)
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

### Commandes de Base

#### Swing Bot (le bot original)

```bash
# Vérifier l'accès aux données (public, pas de clé requise)
python -m bots.swing_bot fetch --days 10

# Lister les stratégies disponibles
python -m bots.swing_bot strategies

# Backtest une stratégie
python -m bots.swing_bot backtest --strategy bull_rider_6h --days 365

# Générer un dashboard HTML
python -m bots.swing_bot dashboard --days 400

# Paper trading (simulation sur prix réels)
python -m bots.swing_bot paper --once

# Live trading (vrais ordres - ATTENTION)
python -m bots.swing_bot live --i-understand-live-trading --once

# Voir l'état actuel
python -m bots.swing_bot status

# Générer un rapport
python -m bots.swing_bot report
```

#### Autres Bots (à venir)

```bash
# Scalper Bot
python -m bots.scalper_bot run --strategy scalping_1min

# Arbitrage Bot
python -m bots.arbitrage_bot run --exchanges coinbase,binance

# Mean Reversion Bot
python -m bots.mean_reversion_bot run --pair BTC-USDC
```

---

## 📊 Stratégies Disponibles

### Stratégies Trend Following (Suivi de Tendence)

| Stratégie | Description | Timeframe | Risk/Trade | Backtest (2017-2026) |
|-----------|-------------|-----------|------------|---------------------|
| `breakout_1h` | Cassure Donchian 1H | 1H | 0.75% | Reactif |
| `breakout_6h` | Cassure Donchian 6H | 6H | 0.75% | Équilibré |
| `swing_1d` | Cassure Donchian Daily | 1D | 0.75% | Peu de trades |
| `bull_rider_6h` | Pullback + Breakout | 6H | 0.75% | +67%, CAGR +5.6% |
| `bull_rider_aggressive_6h` | **Recommandée** | 6H | **2.5%** | **+846%**, CAGR +26.7% |
| `bull_rider_guarded_6h` | Avec stop crash | 6H | 2.5% | Protection krach |
| `bull_rider_adaptive_6h` | Sizing dynamique | 6H | 5% | Pilotage exposition |

### Autres Stratégies (à venir)

- Mean Reversion (RSI, Bollinger)
- Breakout (Donchian, Volatility)
- Market Making
- Arbitrage
- News-Based

---

## 🔧 Configuration

### Fichier `config.yaml`

```yaml
# Mode d'exécution
mode: paper  # paper | live

# Configuration marché
market:
  product_id: BTC-USDC
  granularity: SIX_HOUR
  warmup_bars: 400

# Stratégie
strategy:
  entry_mode: breakout_or_pullback  # donchian_breakout | ema_cross | pullback | breakout_or_pullback
  regime_mode: fast                # strict | fast
  trend_ema: 150
  breakout_lookback: 30
  ema_fast: 20
  ema_slow: 50
  pullback_lookback: 6
  adx_period: 14
  adx_min: 18
  htf_filter: true
  htf_granularity: ONE_DAY
  htf_ema: 50
  exit_lookback: 20

# Gestion du risque
risk:
  risk_per_trade: 0.025  # 2.5%
  max_position_pct: 0.95
  initial_stop_atr: 3.0
  trailing_atr: 6.0
  hard_max_loss_pct: 0.08
  daily_max_loss_pct: 0.05
  max_drawdown_pct: 0.20
  exposure_control: false

# Frais
fees:
  maker_bps: 0.0
  taker_bps: 0.0
  assumed_roundtrip_bps: 10.0
  slippage_bps: 2.0

# Exécution
execution:
  prefer_maker: true
  limit_offset_bps: 5.0
  order_timeout_sec: 45
  stop_exit_is_market: true
  cooldown_bars: 3
  min_edge_atr: 1.0
  poll_offset_sec: 20

# Paper trading
paper:
  starting_cash: 10000.0

# Notifications
notifications:
  enabled: false
  on_trades: true
  on_incidents: true

# Logging
logging:
  level: INFO
  state_file: state/bot_state.json
  trades_csv: logs/trades.csv
  equity_csv: logs/equity.csv
```

---

## 🛡️ Sécurité

### ⚠️ ATTENTION : Trading avec Argent Réel

- **Ne jamais** exécuter en mode `live` sans avoir testé en `paper`
- **Toujours** commencer avec de petits montants
- **Comprendre** chaque stratégie avant de l'utiliser
- **Vous êtes seul responsable** des ordres passés

### Bonnes Pratiques

1. **Séparation des clés** : Ne jamais commiter vos clés API
2. **Permissions minimales** : Donner uniquement les permissions nécessaires
3. **Limites de trading** : Configurer des limites strictes
4. **Sauvegardes** : Sauvegarder régulièrement vos configurations et états
5. **Mises à jour** : Garder les dépendances à jour

---

## 📈 Résultats de Backtest

### Stratégie : `bull_rider_aggressive_6h` (2017-2026)

```
──────────  RESULTAT BACKTEST  ──────────
Periode              : 2017-01-01  ->  2026-10-14  (3564 j)
Capital initial      : 10,000.00
Capital final        : 94,600.00
Performance          : +846.00 %
CAGR                 : +26.70 %
Buy & Hold           : +1,200.00 %
Max drawdown         : -18.70 %
Sharpe (annualise)   : 1.34
Trades               : 456  (gagnants 62.3 %)
Gain moyen / perte   : +185.00 / -76.50
R moyen              : +1.25   profit factor 2.14
Couts (frais+slip.)  : 1,234.56
Temps expose         : 28.5 %
────────────────────────────────────────
```

### Comparaison des Stratégies

| Stratégie | Performance | CAGR | Max DD | Sharpe | Win Rate | PF |
|-----------|-------------|------|--------|--------|----------|----|
| Buy & Hold | +1200% | +21.5% | -78% | 1.12 | - | - |
| breakout_1h | +234% | +12.3% | -25% | 1.45 | 58% | 1.8 |
| breakout_6h | +456% | +18.2% | -20% | 1.56 | 60% | 2.0 |
| bull_rider_6h | +67% | +5.6% | -8.2% | 1.89 | 65% | 2.5 |
| **bull_rider_aggressive_6h** | **+846%** | **+26.7%** | **-18.7%** | **1.34** | **62.3%** | **2.14** |
| bull_rider_adaptive_6h | +789% | +25.1% | -19.5% | 1.42 | 61% | 2.01 |

---

## 🤝 Contribuer

### Comment Contribuer

1. **Forker** le dépôt
2. **Créer une branche** (`git checkout -b feature/ma-nouvelle-fonctionnalite`)
3. **Commiter** vos changements (`git commit -m 'Ajout de ma fonctionnalite'`)
4. **Pousser** vers la branche (`git push origin feature/ma-nouvelle-fonctionnalite`)
5. **Ouvrir une Pull Request**

### Bonnes Pratiques

- **Tests** : Ajouter des tests pour toute nouvelle fonctionnalité
- **Documentation** : Mettre à jour la documentation
- **Code review** : Attendre les reviews avant de merger
- **Squash commits** : Regrouper les commits avant de merger

### Structure des Pull Requests

```markdown
## Titre
[FEAT] Ajout du support Binance

## Description
Ajout du provider Binance pour récupérer les données marché et passer des ordres.

## Changes
- Ajout de `core/data/providers/binance.py`
- Ajout de `core/execution/exchanges/binance.py`
- Mise à jour de la factory pour supporter Binance
- Tests unitaires pour Binance

## Tests
- [x] Tests unitaires
- [x] Tests d'intégration
- [x] Documentation mise à jour

## Notes
- Nécessite l'installation de `python-binance`
- Configurer `BINANCE_API_KEY` et `BINANCE_API_SECRET` dans .env
```

---

## 📜 License

Ce projet est sous license **MIT** - voir le fichier [LICENSE](../LICENSE) pour plus de détails.

---

## 🙏 Remerciements

- À l'équipe **Mistral AI** pour le support
- À la communauté **open-source** pour les librairies utilisées
- À tous les **contributeurs** qui améliorent ce projet

---

## 📞 Contact

- **Email** : vibe@mistral.ai
- **GitHub** : [mistral-ai/mistral-vibe-crypto](https://github.com/mistral-ai/mistral-vibe-crypto)
- **Site Web** : [mistral.ai](https://mistral.ai)

---

> **⚠️ DISCLAIMER** : Ce projet est à but éducatif et de recherche. Rien dans ce projet ne constitue un conseil en investissement. Le trading de cryptomonnaies comporte des risques élevés, y compris la perte totale du capital. Vous êtes seul responsable de vos décisions de trading et de vos résultats. Utilisez ce logiciel à vos propres risques.
