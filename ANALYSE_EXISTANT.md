# Analyse du Projet de Trading Crypto Existant

## Date : 14 Octobre 2026
## Contexte : Bot de Trading Swing pour Coinbase Advanced Trade

---

## Table des Matières
1. [Vue d'Ensemble](#vue-densemble)
2. [Architecture du Projet](#architecture-du-projet)
3. [Détail des Composants](#détail-des-composants)
4. [Stratégies Implémentées](#stratégies-implémentées)
5. [Points Forts](#points-forts)
6. [Points à Améliorer](#points-à-améliorer)
7. [Recommandations pour Mistral Vibe](#recommandations-pour-mistral-vibe)
8. [Prochaines Étapes](#prochaines-étapes)

---

## Vue d'Ensemble

### Structure Globale
```
crypto/
├── README.md                      # Documentation principale
├── python-swing-bot/              # Approche unique actuelle
│   ├── bot/                       # Code source principal
│   │   ├── __main__.py            # CLI principal
│   │   ├── __init__.py
│   │   ├── analysis.py            # Analyse approfondie (walk-forward, régimes)
│   │   ├── backtest.py            # Moteur de backtest
│   │   ├── broker.py              # Abstraction courtier (Paper/Live)
│   │   ├── coinbase_client.py     # Client API Coinbase
│   │   ├── config.py              # Gestion configuration
│   │   ├── dashboard.py           # Génération dashboard HTML
│   │   ├── engine.py              # Moteur principal
│   │   ├── exposure.py            # Pilotage dynamique exposition
│   │   ├── indicators.py          # Indicateurs techniques
│   │   ├── journal.py             # Journalisation trades/equity
│   │   ├── logging_setup.py       # Configuration logging
│   │   ├── notify.py              # Notifications Telegram
│   │   ├── report.py              # Génération rapports
│   │   └── risk.py                # Gestion du risque
│   ├── config.yaml                # Configuration de base
│   ├── strategies.yaml            # Presets de stratégies
│   ├── requirements.txt           # Dépendances
│   ├── requirements-dev.txt       # Dépendances dev
│   ├── data/                      # Données backtest
│   ├── logs/                      # Journaux d'exécution
│   ├── state/                     # État du bot
│   └── .venv/                     # Environnement virtuel
└── python-swing-bot-portable.zip  # Archive portable
```

### Technologie
- **Langage** : Python 3.12+
- **Framework** : CLI natif (argparse)
- **Dependencies** : 
  - `coinbase-advanced-py>=1.7.0` (SDK officiel Coinbase)
  - `pandas>=2.0`, `numpy>=1.24`
  - `PyYAML>=6.0`, `python-dotenv>=1.0`
  - `requests>=2.31`
  - `matplotlib>=3.7`

---

## Architecture du Projet

### Pattern Design
Le projet suit une **architecture modulaire et découpée** :

1. **Séparation des responsabilités** (Single Responsibility Principle)
   - Chaque fichier a un rôle précis
   - Pas de couplage fort entre composants

2. **Inversion de dépendance**
   - Interface `Broker` abstraite
   - Implémentations `PaperBroker` et `LiveBroker`
   - Injection de dépendances dans le moteur

3. **Configuration centralisée**
   - Fichier YAML pour la configuration
   - Surcharge par presets (strategies.yaml)
   - Variables d'environnement pour les secrets

4. **Pattern Strategy**
   - `TrendStrategy` encapsule la logique de trading
   - Facile à étendre avec de nouvelles stratégies

### Flux Principal
```
CLI (__main__.py)
  ↓
Chargement Config (config.py)
  ↓
Initialisation Moteur (engine.py)
  ↓
Boucle Principale (run → tick)
  ├── Chargement données marché (coinbase_client.py)
  ├── Évaluation stratégie (strategy.py)
  ├── Gestion position (risk.py)
  ├── Exécution ordres (broker.py)
  ├── Journalisation (journal.py)
  └── Notifications (notify.py)
```

---

## Détail des Composants

### 1. Moteur (engine.py)
**Rôle** : Orchestre le cycle de vie du bot

**Fonctionnalités clés** :
- Gestion du tick (1 décision par bougie clôturée)
- Boucle d'exécution avec sleep intelligent
- Gestion des états (position, cooldown, halt)
- Gestion des garde-fous (kill switches)
- Intégration avec tous les autres modules

**Points forts** :
- Code propre et bien structuré
- Gestion robuste des erreurs
- Mécanismes de sécurité intégrés (stop loss, drawdown max, etc.)
- Support multi-produits (BTC-USDC, ETH-USDC)

### 2. Stratégie (strategy.py)
**Rôle** : Logique de décision de trading

**Indicateurs utilisés** :
- EMA (20, 50, 150, 200) pour la tendance
- ADX pour la force de tendance
- Donchian Channel pour les cassures
- ATR pour la volatilité

**Modes d'entrée** :
- `donchian_breakout` : Cassure du plus haut
- `ema_cross` : Croisement EMA rapide/lente
- `pullback` : Rachat de repli sur EMA rapide
- `breakout_or_pullback` : Combinaison des deux

**Modes de régime** :
- `strict` : Prix > EMA + pente EMA > 0
- `fast` : Prix > EMA + EMA rapide > EMA lente

**Filtres** :
- Filtre HTF (Higher Time Frame) : validation sur daily
- Filtre ADX : évite les marchés en range

### 3. Gestion du Risque (risk.py)
**Rôle** : Protection du capital

**Mécanismes** :
- Stop initial basé sur ATR
- Stop suiveur "chandelier" (trailing stop)
- Passage au point mort (breakeven)
- Plancher de perte dur (hard max loss)
- Limite de perte journalière
- Limite de drawdown global

**StopManager** :
- Gère le stop pour une position ouverte
- Le stop ne redescend jamais (effet cliquet)
- Intègre tous les mécanismes de protection

### 4. Exposure (exposure.py)
**Rôle** : Pilotage dynamique de l'exposition

**4 briques** (activées par `risk.exposure_control`) :
1. **Vol Targeting** : Taille ajustée selon volatilité
   - `taille *= clip(vol_ref / ATR%_courant, floor, cap)`
   - Un krach = pic de vol → taille tombe

2. **Frein de Krach** : Sortie immédiate sur chute brutale
   - Déclenché si rendement N bougies < -K*ATR%
   - Ou si close << EMA rapide
   - Bloque les entrées pendant M bougies

3. **Throttle Drawdown** : Réduction linéaire après -X% du pic
   - Réduction de -10% à -20% du pic
   - Taille minimale configurable

4. **Anti-Whipsaw** : Réduction après sortie
   - Taille /2 pendant K bougies après sortie
   - Évite les faux rebonds

### 5. Backtest (backtest.py)
**Rôle** : Test des stratégies sur historique

**Fonctionnalités** :
- Simulation précise avec frais et slippage
- Métriques complètes : CAGR, Sharpe, max drawdown, etc.
- Export CSV des trades et equity curve
- Support des indicateurs d'exposition

**Métriques calculées** :
- Performance totale et annualisée
- Buy & Hold comparison
- Max drawdown
- Sharpe ratio
- Win rate, profit factor
- Temps en position
- Coûts (frais + slippage)

### 6. Analyse (analysis.py)
**Rôle** : Validation approfondie

**Fonctionnalités** :
- Découpage en régimes haussier/baissier
- Walk-forward validation
- Analyse de sensibilité
- Comparaison multi-stratégies

### 7. Dashboard (dashboard.py)
**Rôle** : Visualisation HTML autonome

**Contenu** :
- Snapshot des indicateurs marché
- Comparaison backtests toutes stratégies
- Courbes d'equity et drawdown superposées
- Signaux actuels de chaque stratégie

### 8. Client Coinbase (coinbase_client.py)
**Rôle** : Interaction avec Coinbase API

**Fonctionnalités** :
- Récupération candles historiques (public, sans clé)
- Spot price en temps réel
- Passage d'ordres (limit, market)
- Gestion des fills et timeouts
- Cache optionnel

**Particularités** :
- Gestion des pagination (300 candles max par requête)
- Retry sur erreurs 429/500
- Support des ordres post-only (maker)

### 9. Broker (broker.py)
**Rôle** : Abstraction du courtier

**Interface** :
```python
class Broker(ABC):
    get_cash() -> float
    get_position() -> Position
    mark_price(price: float) -> None
    equity(mark: float) -> float
    buy(qty, ref_price, maker) -> Fill
    sell(qty, ref_price, maker) -> Fill
```

**Implémentations** :
- `PaperBroker` : Simulation sur prix réels
- `LiveBroker` : Vrais ordres sur Coinbase

### 10. Configuration (config.py)
**Rôle** : Gestion centralisée de la configuration

**Structure** :
- Dataclasses pour chaque section (Market, Strategy, Risk, etc.)
- Validation des valeurs
- Fusion recursive des presets
- Support multi-produits (fichiers nommés par produit)

**Sources** :
1. Fichier YAML principal (config.yaml)
2. Presets (strategies.yaml)
3. Variables d'environnement (.env)
4. Arguments CLI

---

## Stratégies Implémentées

### Stratégie de Base : Suivi de Tendence Haussière (Long-Only)

**Philosophie** :
1. **Ne pas se faire piéger** → Stop loss sérieux
2. **Profiter des vraies tendances haussières** → Entrée sur confirmation
3. **Minimiser les frais** → Ordres maker post-only

### Presets Disponibles (strategies.yaml)

| Stratégie | Granularité | Entry Mode | Risk/Trade | Trailing ATR | Régime | Backtest (2017-2026) |
|-----------|-------------|------------|------------|--------------|--------|---------------------|
| breakout_1h | 1H | donchian | 0.75% | - | strict | Reactif, + de trades |
| breakout_6h | 6H | donchian | 0.75% | - | strict | Bon compromis |
| swing_1d | 1D | donchian | 0.75% | - | strict | Peu de trades |
| bull_rider_6h | 6H | breakout_or_pullback | 0.75% | 5.0 | strict | +67%, CAGR +5.6% |
| bull_rider_aggressive_6h | 6H | breakout_or_pullback | **2.5%** | **6.0** | **fast** | **+846%**, CAGR +26.7%, maxDD -18.7% |
| bull_rider_guarded_6h | 6H | breakout_or_pullback | 2.5% | 6.0 | fast | + stop crash bougie (-5%) |
| bull_rider_max_6h | 6H | breakout_or_pullback | **5%** | 6.0 | fast | Sizing maximum |
| bull_rider_adaptive_6h | 6H | breakout_or_pullback | 5% | 6.0 | fast | + exposure_control |
| ema_cross_6h | 6H | ema_cross | 0.75% | - | strict | Croisement 20/50 |
| conservative_6h | 6H | donchian | 0.5% | 4.0 | strict | Prudent |
| aggressive_1h | 1H | donchian | 1.5% | - | strict | Agressif |

**Stratégie Active** : `bull_rider_aggressive_6h`

### Début des Presets Agressifs
Les stratégies `bull_rider_*` représentent l'évolution la plus sophistiquée :

**bull_rider_aggressive_6h** (ACTIVE) :
- Risk per trade : 2.5% (vs 0.75% default)
- Régime mode : `fast` (EMA150 + EMA20 > EMA50)
- Initial stop ATR : 3.0
- Trailing ATR : 6.0
- Max drawdown : 20%
- Résultats : +846%, CAGR +26.7%, Sharpe 1.34

**bull_rider_adaptive_6h** :
- Même sizing que max_6h (5%)
- **exposure_control : true**
- Vol targeting : taille ajustée selon volatilité
- Frein de krach : sortie sur chute brutale
- Throttle DD : réduction à -10% du pic
- Anti-whipsaw : réduction après sortie

---

## Points Forts

### ✅ Architecture
1. **Modularité** : Chaque composant est isolé et testable
2. **Extensibilité** : Facile d'ajouter de nouvelles stratégies
3. **Séparation des concerns** : Code bien organisé
4. **Configuration flexible** : YAML + presets + env vars
5. **Multi-produits** : Support BTC-USDC et ETH-USDC en parallèle

### ✅ Fonctionnalités
1. **Gestion du risque avancée** : Multiples niveaux de protection
2. **Backtest robuste** : Métriques complètes, frais réalistes
3. **Paper trading** : Simulation sur prix réels
4. **Live trading** : Intégration Coinbase API
5. **Dashboard HTML** : Visualisation professionnelle
6. **Notifications Telegram** : Alertes en temps réel
7. **Pilotage d'exposition** : 4 mécanismes de contrôle dynamique

### ✅ Qualité de Code
1. **Typage** : Utilisation intensive de dataclasses et type hints
2. **Tests** : Suite de tests complète (pytest)
3. **Documentation** : Docstrings et commentaires détaillés
4. **Logging** : Journalisation complète
5. **Gestion d'erreurs** : Robuste et gracefull

---

## Points à Améliorer

### ⚠️ Architecture
1. **Pas de tests d'intégration** : Tests unitaires seulement
2. **Couplage résiduel** : Certains modules dépendent directement d'autres
3. **Pas de pattern Repository** : Données marché chargées à la volée
4. **Pas de cache persistant** : Cache en mémoire seulement

### ⚠️ Fonctionnalités
1. **Un seul exchange** : Coinbase seulement (pas Binance, Kraken, etc.)
2. **Pas de short selling** : Long-only seulement
3. **Pas de leveraged trading** : Spot seulement
4. **Pas de multi-paires simultanées** : Une paire à la fois par instance
5. **Pas de portfolio management** : Gestion isolée par paire
6. **Pas de machine learning** : Approche purement technique

### ⚠️ Performance
1. **Pas d'optimisation vectorisée** : Boucle barre par barre
2. **Pas de parallélisation** : Backtests séquentiels
3. **Chargement données lent** : Requêtes API séquentielles

### ⚠️ Qualité de Code
1. **Fichiers longs** : Certains fichiers > 300 lignes
2. **Duplication** : Logique similaire dans engine.py et backtest.py
3. **Pas de type checking strict** : Pas de mypy en CI
4. **Pas de coverage** : Pas de mesure de couverture de tests

### ⚠️ Opérationnel
1. **Pas de CI/CD** : Tests manuels seulement
2. **Pas de monitoring** : Métriques en logs seulement
3. **Pas de metrics aggregées** : Pas de Prometheus/Grafana
4. **Pas de déploiement automatisé** : Déploiement manuel

---

## Recommandations pour Mistral Vibe

### 🎯 Priorités Imédiates

#### 1. **Créer une librairie partagée**
```
mistral-vibe-crypto/
├── core/                          # Librairie réutilisable
│   ├── __init__.py
│   ├── indicators.py              # Indicateurs techniques (déjà bien)
│   ├── data/                      # Module données marché
│   │   ├── __init__.py
│   │   ├── providers/             # Multi-exchanges
│   │   │   ├── coinbase.py        # Refactored
│   │   │   ├── binance.py         # À ajouter
│   │   │   └── kraken.py          # À ajouter
│   │   └── cache.py               # Cache persistant
│   ├── strategies/                # Stratégies standardisées
│   │   ├── __init__.py
│   │   ├── base.py                # Interface Strategy
│   │   ├── trend_following.py      # Actuel
│   │   ├── mean_reversion.py      # À ajouter
│   │   └── breakout.py            # À ajouter
│   ├── risk/                       # Gestion du risque
│   │   ├── __init__.py
│   │   ├── stop_manager.py         # Refactored
│   │   ├── exposure.py             # Refactored
│   │   └── portfolio.py            # À ajouter
│   └── utils/                      # Utilitaires
│       ├── __init__.py
│       ├── config.py              # Refactored
│       ├── logging.py              # Refactored
│       └── types.py                # Types communs
└── bots/                          # Bots spécifiques
    ├── swing-bot/                  # Version améliorée
    ├── scalper-bot/                # À créer
    └── arbitrage-bot/              # À créer
```

#### 2. **Standardiser les interfaces**

```python
# Interface Strategy
class Strategy(ABC):
    @abstractmethod
    def min_bars(self) -> int: ...
    
    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.DataFrame: ...
    
    @abstractmethod
    def evaluate(self, df: pd.DataFrame, in_position: bool) -> Signal: ...

# Interface DataProvider
class DataProvider(ABC):
    @abstractmethod
    def get_candles(self, product: str, granularity: str, n_bars: int) -> pd.DataFrame: ...
    
    @abstractmethod
    def get_spot_price(self, product: str) -> float: ...
    
    @abstractmethod
    def get_orderbook(self, product: str) -> dict: ...

# Interface Broker
class Broker(ABC):
    @abstractmethod
    def get_balance(self, currency: str) -> float: ...
    
    @abstractmethod
    def create_order(self, order: Order) -> OrderResponse: ...
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool: ...
```

#### 3. **Améliorer le Backtesting**

**À implémenter** :
1. **Parallélisation** : Backtests concurrentes
2. **Walk-forward optimisé** : Moins de duplication de code
3. **Monte Carlo** : Simulation de scénarios
4. **Stress testing** : Scénarios extrêmes
5. **Benchmarking** : Comparaison avec indices

**Exemple** :
```python
from concurrent.futures import ThreadPoolExecutor

def run_parallel_backtests(strategies: list, n_workers: int = 4):
    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        results = list(executor.map(run_single_backtest, strategies))
    return results
```

#### 4. **Ajouter le Support Multi-Exchange**

**Architecture recommandée** :
```python
class ExchangeFactory:
    @staticmethod
    def create(exchange_name: str, api_key: str, api_secret: str) -> Exchange:
        if exchange_name == "coinbase":
            return CoinbaseExchange(api_key, api_secret)
        elif exchange_name == "binance":
            return BinanceExchange(api_key, api_secret)
        # ...

class Exchange(ABC):
    @abstractmethod
    def get_data_provider(self) -> DataProvider: ...
    
    @abstractmethod
    def get_broker(self) -> Broker: ...
```

#### 5. **Implémenter le Portfolio Management**

**Concepts** :
- Allocation dynamique entre paires
- Correlation-based positioning
- Risk parity
- Mean-variance optimization

**Exemple** :
```python
class PortfolioManager:
    def __init__(self, strategies: list[Strategy], risk_budget: dict):
        self.strategies = strategies
        self.risk_budget = risk_budget  # {strategy_name: weight}
    
    def allocate_capital(self, total_capital: float) -> dict:
        # Allocation basée sur risque, corrélation, performance
        pass
```

### 📊 Metrics et Monitoring

**À implémenter** :
1. **Prometheus metrics** : Equity, drawdown, trades, etc.
2. **Grafana dashboards** : Visualisation temps réel
3. **Alerting** : Seuils de drawdown, erreurs, etc.
4. **Logging structuré** : JSON logs pour analyse

**Exemple** :
```python
from prometheus_client import Gauge, Counter

BOT_EQUITY = Gauge('bot_equity', 'Current equity', ['bot_id', 'strategy'])
BOT_DRAWDOWN = Gauge('bot_drawdown', 'Current drawdown %', ['bot_id'])
BOT_TRADES = Counter('bot_trades', 'Number of trades', ['bot_id', 'side'])
```

### ⚡ Optimisation des Performances

**À implémenter** :
1. **Cache Redis** : Pour les données marché
2. **Vectorisation** : Utilisation numpy/pandas optimisée
3. **Batch processing** : Traitement par lots
4. **Async I/O** : Pour les requêtes API

**Exemple** :
```python
import aiohttp
import asyncio

async def fetch_candles_async(product: str, granularity: str, n_bars: int) -> pd.DataFrame:
    async with aiohttp.ClientSession() as session:
        # Requêtes async
        pass
```

### 🤖 Machine Learning (Optionnel)

**Idées** :
1. **Feature engineering** : Créer des features à partir des indicateurs
2. **Classification** : Prédire la direction du marché
3. **Regression** : Prédire la magnitude du mouvement
4. **Reinforcement Learning** : Optimisation dynamique
5. **Anomaly Detection** : Détecter les régimes de marché

**Exemple** :
```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# Création de features
features = ['ema_20', 'ema_50', 'adx', 'rsi', 'atr_pct', 'volume_chg']
target = 'up_down'  # +1 si close_{t+1} > close_t, -1 sinon

# Entraînement
X_train, X_test, y_train, y_test = train_test_split(df[features], df[target])
model = RandomForestClassifier(n_estimators=100)
model.fit(X_train, y_train)
```

---

## Prochaines Étapes

### Phase 1 : Refactoring (1-2 semaines)
- [ ] Créer la structure `mistral-vibe-crypto/`
- [ ] Extraire les composants réutilisables
- [ ] Standardiser les interfaces
- [ ] Ajouter des tests d'intégration
- [ ] Documenter la nouvelle architecture

### Phase 2 : Améliorations (2-3 semaines)
- [ ] Implémenter le support multi-exchange
- [ ] Ajouter Binance et Kraken
- [ ] Implémenter le portfolio management
- [ ] Paralléliser les backtests
- [ ] Optimiser les performances

### Phase 3 : Nouveaux Bots (3-4 semaines)
- [ ] Créer un bot de scalping (1min-5min)
- [ ] Créer un bot d'arbitrage (multi-exchange)
- [ ] Créer un bot mean-reversion
- [ ] Créer un bot breakout
- [ ] Ajouter le support short selling

### Phase 4 : Production (2-3 semaines)
- [ ] Mettre en place CI/CD
- [ ] Configurer le monitoring
- [ ] Déployer en production
- [ ] Mettre en place l'alerting
- [ ] Documenter les opérations

### Phase 5 : Recherche (Optionnel)
- [ ] Expérimenter avec ML
- [ ] Tester de nouvelles stratégies
- [ ] Optimiser les paramètres
- [ ] Backtester sur plus de données
- [ ] Publier les résultats

---

## Conclusion

Le projet existant est **déjà très solide** avec :
- Une architecture modulaire et bien conçue
- Une gestion du risque sophistiquée
- Des fonctionnalités complètes (backtest, paper, live)
- Une suite de tests correcte
- Une documentation claire

**Mistral Vibe peut** :
1. **Capitaliser sur l'existant** : Réutiliser la base de code
2. **Apporter de la valeur ajoutée** : Multi-exchange, portfolio management, ML
3. **Industrialiser** : CI/CD, monitoring, déploiement
4. **Innover** : Nouvelles stratégies, nouveaux bots

**Recommandation** : Commencer par le refactoring et la création de la librairie partagée avant d'ajouter de nouvelles fonctionnalités. Cela permettra de maximiser la réutilisation du code et de faciliter la maintenance.
