# Architecture Technique - Mistral Vibe Crypto

## 🏗️ Vue d'Ensemble

L'architecture de **Mistral Vibe Crypto** suit les principes **SOLID**, **DRY** et **KISS** pour créer une plateforme modulaire, extensible et maintenable.

---

## 🎯 Principes de Conception

### 1. Modularité
Chaque composant est **indépendant** et peut être :
- Développé séparément
- Testé isolément
- Remplacé sans impact sur le reste

### 2. Inversion de Dépendances
- Les modules de haut niveau **ne dépendent pas** des modules de bas niveau
- Les deux dépendent **d'abstractions** (interfaces)
- Les abstractions ne dépendent **pas des implémentations**

### 3. Séparation des Responsabilités
Chaque classe/module a **une seule raison de changer** (Single Responsibility Principle).

### 4. Ouvert/Fermé (Open/Closed)
- Les entités doivent être **ouvertes à l'extension**
- Mais **fermées à la modification**

### 5. Configuration par Convention
- Convention de nommage claire
- Structure de fichiers standardisée
- Configuration par défaut intelligente

---

## 📦 Structure des Packages

```
mistral-vibe-crypto/
├── core/                          # 🏗️ Librairie principale (réutilisable)
│   ├── __init__.py                # Exports publics
│   ├── types.py                   # Types communs (dataclasses, enums)
│   │
│   ├── indicators/                # 📊 Indicateurs techniques
│   │   ├── __init__.py            # Exports
│   │   ├── base.py                # Indicator ABC
│   │   ├── trend.py               # EMA, SMA, slope, etc.
│   │   ├── volatility.py           # ATR, True Range, etc.
│   │   ├── momentum.py             # ADX, RSI, MACD, etc.
│   │   ├── volume.py              # OBV, Volume SMA, etc.
│   │   └── patterns.py             # Donchian, Candlestick patterns
│   │
│   ├── data/                      # 📥 Données marché
│   │   ├── __init__.py
│   │   ├── providers/             # Providers par exchange
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # DataProvider ABC
│   │   │   ├── coinbase.py        # Coinbase Advanced Trade
│   │   │   ├── binance.py         # Binance Spot & Futures
│   │   │   ├── kraken.py          # Kraken
│   │   │   └── ...
│   │   ├── cache/                 # Cache des données
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Cache ABC
│   │   │   ├── memory_cache.py    # Cache en mémoire
│   │   │   └── redis_cache.py     # Cache Redis
│   │   └── factory.py             # Factory de providers
│   │
│   ├── strategies/                # 🎯 Stratégies de trading
│   │   ├── __init__.py
│   │   ├── base.py                # Strategy ABC
│   │   ├── trend_following.py      # Suivi de tendance (existant)
│   │   ├── mean_reversion.py      # Retour à la moyenne
│   │   ├── breakout.py            # Cassures
│   │   ├── market_making.py       # Market making
│   │   ├── arbitrage.py           # Arbitrage
│   │   ├── news_based.py          # Basé sur les news
│   │   └── factory.py             # Factory de stratégies
│   │
│   ├── risk/                       # 🛡️ Gestion du risque
│   │   ├── __init__.py
│   │   ├── stop_manager.py         # Gestion des stops (existant)
│   │   ├── exposure.py             # Pilotage exposition (existant)
│   │   ├── portfolio.py            # Gestion portefeuille
│   │   ├── position_sizing.py      # Calcul de taille de position
│   │   └── drawdown_manager.py     # Gestion des drawdowns
│   │
│   ├── execution/                 # ⚡ Exécution des ordres
│   │   ├── __init__.py
│   │   ├── broker.py              # Broker ABC
│   │   ├── paper_broker.py        # Simulation (existant)
│   │   ├── live_broker.py          # Base pour live brokers
│   │   └── exchanges/              # Brokers par exchange
│   │       ├── __init__.py
│   │       ├── base.py            # ExchangeBroker ABC
│   │       ├── coinbase.py        # Coinbase (existant refactorisé)
│   │       ├── binance.py         # Binance
│   │       ├── kraken.py          # Kraken
│   │       └── ...
│   │
│   ├── backtesting/                # 📈 Backtesting
│   │   ├── __init__.py
│   │   ├── engine.py               # Moteur de backtest (existant refactorisé)
│   │   ├── walkforward.py          # Walk-forward validation
│   │   ├── montecarlo.py           # Simulation Monte Carlo
│   │   ├── metrics.py              # Calcul des métriques
│   │   └── reporter.py             # Génération de rapports
│   │
│   └── utils/                      # 🔧 Utilitaires
│       ├── __init__.py
│       ├── config.py              # Gestion configuration (existant)
│       ├── logging.py              # Configuration logging (existant)
│       ├── validators.py           # Validateurs
│       ├── helpers.py              # Fonctions utilitaires
│       └── exceptions.py            # Exceptions custom
│
├── bots/                          # 🤖 Bots de trading
│   ├── __init__.py
│   ├── swing_bot/                  # Bot swing trading (existant refactorisé)
│   │   ├── __init__.py
│   │   ├── __main__.py             # CLI
│   │   ├── config.yaml             # Configuration
│   │   └── strategies.yaml         # Presets de stratégies
│   ├── scalper_bot/                # Bot scalping
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   └── config.yaml
│   ├── arbitrage_bot/              # Bot arbitrage
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   └── config.yaml
│   ├── mean_reversion_bot/        # Bot mean reversion
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   └── config.yaml
│   └── ...
│
├── tests/                         # 🧪 Tests
│   ├── __init__.py
│   ├── conftest.py                # Fixtures pytest
│   ├── unit/                      # Tests unitaires
│   │   ├── __init__.py
│   │   ├── test_types.py
│   │   ├── test_indicators/
│   │   │   ├── __init__.py
│   │   │   ├── test_trend.py
│   │   │   ├── test_volatility.py
│   │   │   └── ...
│   │   ├── test_data_providers/
│   │   │   ├── __init__.py
│   │   │   ├── test_coinbase.py
│   │   │   └── ...
│   │   └── ...
│   └── integration/                # Tests d'intégration
│       ├── __init__.py
│       ├── test_swing_bot.py
│       ├── test_portfolio.py
│       └── ...
│
├── docs/                          # 📚 Documentation
│   ├── ARCHITECTURE.md            # Ce fichier
│   ├── API.md                     # Documentation API
│   ├── DEVELOPMENT.md             # Guide de développement
│   ├── DEPLOYMENT.md              # Guide de déploiement
│   └── EXAMPLES.md                # Exemples d'utilisation
│
├── scripts/                       # 📜 Scripts utilitaires
│   ├── __init__.py
│   ├── fetch_data.py              # Récupération de données
│   ├── backtest_all.py            # Backtest toutes stratégies
│   ├── generate_dashboard.py      # Génération dashboard
│   └── ...
│
├── .env.example                   # Exemple de variables d'environnement
├── .gitignore                     # Exclusions Git
├── pyproject.toml                 # Configuration projet
├── setup.py                      # Script d'installation
├── requirements.txt               # Dépendances
└── README.md                      # Documentation principale
```

---

## 🔌 Diagrammes d'Architecture

### Diagramme de Composants

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Mistral Vibe Crypto                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐   │
│  │     CLI         │    │   Configuration  │    │    Logging       │   │
│  │  (argparse)      │    │   (YAML, .env)   │    │   (structlog)     │   │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘   │
│           │                         │                        │            │
│           └─────────────────────────┼────────────────────────┘            │
│                                     ▼                                         │
│                    ┌─────────────────────────────────┐                    │
│                    │         Bot Application          │                    │
│                    │   (SwingBot, ScalperBot, etc.)    │                    │
│                    └─────────────────┬───────────────┘                    │
│                                          │                                    │
│                     ┌────────────────────┼─────────────────────┐           │
│                     ▼                    ▼                     ▼           │
│              ┌────────────┐    ┌────────────┐      ┌────────────┐      │
│              │   Engine    │    │  Backtest   │      │  Dashboard  │      │
│              │   (Moteur)  │    │   (Test)    │      │   (Visual)  │      │
│              └──────┬──────┘    └──────┬──────┘      └──────┬──────┘      │
│                     │                   │                     │             │
│                     ▼                   ▼                     ▼             │
│              ┌──────────────────────────────────────────────────┐        │
│              │                    Core Library                     │        │
│              │   (Indicateurs, Data, Strategies, Risk, Execution)  │        │
│              └───────────────┬───────────────┬───────────────┘        │
│                          │               │               │                │
│                          ▼               ▼               ▼                │
│                   ┌──────────┐   ┌──────────┐   ┌──────────┐          │
│                   │Indicators│   │  Data    │   │Strategies│          │
│                   └──────────┘   └──────────┘   └──────────┘          │
│                          │               │               │                │
│                          ▼               ▼               ▼                │
│                   ┌────────────────────────────────────────────┐  │
│                   │                External Services                 │  │
│                   │  (Coinbase API, Binance API, Redis, etc.)      │  │
│                   └────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Diagramme de Séquence (Tick de Trading)

```
CLI/User          Bot          Engine          Strategy      DataProvider
  │               │              │               │              │
  │── run() ───────▶│              │               │              │
  │               │── run() ──────▶│               │              │
  │               │              │── tick() ──────▶│              │
  │               │              │               │── evaluate()─▶│
  │               │              │               │              │── get_candles()
  │               │              │               │◀── return df
  │               │              │               │── compute()
  │               │              │               │── signal_from_row()
  │               │              │◀── return Signal
  │               │              │── _manage_position()
  │               │              │── _maybe_enter()
  │               │              │               │              │
  │               │              │── Broker.buy/sell()
  │               │              │              │
  │               │◀── return    │              │
  │◀── results    │              │              │
```

---

## 🔧 Modules Principaux

### 1. Module `core.types`

**Rôle** : Définir tous les types communs utilisés dans la plateforme.

**Classes principales** :
- `ExchangeEnum` : Liste des exchanges supportés
- `GranularityEnum` : Granularités (timeframes)
- `OrderTypeEnum` : Types d'ordres
- `OrderSideEnum` : Sides d'ordre (BUY/SELL)
- `LiquidityEnum` : Type de liquidité (MAKER/TAKER)
- `SignalActionEnum` : Actions de signal
- `Candle` : Représente une bougie OHLCV
- `Order` : Représente un ordre
- `Fill` : Représente un fill (exécution)
- `Position` : Représente une position
- `Signal` : Représente un signal de trading
- `Trade` : Représente un trade complet

**Exemple** :
```python
from mistral_vibe_crypto.core.types import Signal, SignalActionEnum

signal = Signal(
    action=SignalActionEnum.ENTER_LONG,
    price=50000.0,
    atr=1000.0,
    reason="Cassure Donchian",
    regime_ok=True,
    adx=25.0
)
```

---

### 2. Module `core.indicators`

**Rôle** : Calculer les indicateurs techniques.

**Architecture** :
```
indicators/
├── base.py          # Indicator ABC
├── trend.py         # Indicateurs de tendance
├── volatility.py     # Indicateurs de volatilité
├── momentum.py      # Indicateurs de momentum
├── volume.py        # Indicateurs de volume
└── patterns.py      # Patterns de prix
```

**Classes/Interfaces** :

```python
from abc import ABC, abstractmethod
import pandas as pd

class Indicator(ABC):
    """Interface de base pour un indicateur."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def required_columns(self) -> list[str]:
        pass
    
    @abstractmethod
    def compute(self, df: pd.DataFrame, **kwargs) -> pd.Series:
        pass
```

**Fonctions utilitaires** (approche fonctionnelle) :
```python
# Dans trend.py
def ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=span, adjust=False).mean()

def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window).mean()
```

---

### 3. Module `core.data`

**Rôle** : Récupérer et gérer les données marché.

**Architecture** :
```
data/
├── providers/
│   ├── base.py            # DataProvider ABC
│   ├── coinbase.py        # Coinbase Implementation
│   ├── binance.py         # Binance Implementation
│   └── kraken.py          # Kraken Implementation
├── cache/
│   ├── base.py            # Cache ABC
│   ├── memory_cache.py    # In-memory cache
│   └── redis_cache.py     # Redis cache
└── factory.py             # Provider Factory
```

**DataProvider Interface** :
```python
from abc import ABC, abstractmethod
from mistral_vibe_crypto.core.types import GranularityEnum, ProductId

class DataProvider(ABC):
    """Interface pour un provider de données."""
    
    @abstractmethod
    def get_candles(
        self,
        product_id: ProductId,
        granularity: GranularityEnum,
        n_bars: int,
    ) -> pd.DataFrame:
        pass
    
    @abstractmethod
    def get_spot_price(self, product_id: ProductId) -> float:
        pass
    
    @abstractmethod
    def get_orderbook(self, product_id: ProductId, depth: int = 10) -> dict:
        pass
```

**Factory Pattern** :
```python
class DataProviderFactory:
    _providers = {
        ExchangeEnum.COINBASE: CoinbaseProvider,
        ExchangeEnum.BINANCE: BinanceProvider,
    }
    
    @classmethod
    def create(cls, exchange: ExchangeEnum) -> DataProvider:
        provider_class = cls._providers.get(exchange)
        if provider_class is None:
            raise ValueError(f"Unsupported exchange: {exchange}")
        return provider_class()
```

---

### 4. Module `core.strategies`

**Rôle** : Implémenter les stratégies de trading.

**Architecture** :
```
strategies/
├── base.py                # Strategy ABC
├── trend_following.py      # Suivi de tendance
├── mean_reversion.py      # Retour à la moyenne
├── breakout.py            # Cassures
├── market_making.py       # Market making
├── arbitrage.py           # Arbitrage
└── factory.py             # Strategy Factory
```

**Strategy Interface** :
```python
from abc import ABC, abstractmethod
import pandas as pd
from mistral_vibe_crypto.core.types import Signal, ProductId

class Strategy(ABC):
    """Interface de base pour une stratégie."""
    
    @abstractmethod
    def min_bars(self) -> int:
        """Nombre minimum de bougies requises."""
        pass
    
    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcule les indicateurs nécessaires."""
        pass
    
    @abstractmethod
    def evaluate(
        self,
        df: pd.DataFrame,
        in_position: bool,
        product_id: ProductId,
    ) -> Signal:
        """Évalue le signal pour la dernière bougie."""
        pass
```

**Exemple d'implémentation** (`trend_following.py`) :
```python
class TrendFollowingStrategy(Strategy):
    def __init__(
        self,
        trend_ema: int = 200,
        adx_period: int = 14,
        adx_min: float = 22.0,
        breakout_lookback: int = 20,
    ):
        self.trend_ema = trend_ema
        self.adx_period = adx_period
        self.adx_min = adx_min
        self.breakout_lookback = breakout_lookback
    
    def min_bars(self) -> int:
        return max(self.trend_ema, self.adx_period, self.breakout_lookback) + 5
    
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["ema_trend"] = ema(out["close"], self.trend_ema)
        out["adx"] = adx(out["high"], out["low"], out["close"], self.adx_period)
        out["breakout_high"] = donchian_high(out["close"], self.breakout_lookback)
        return out
    
    def evaluate(self, df: pd.DataFrame, in_position: bool) -> Signal:
        data = self.compute(df)
        last = data.iloc[-1]
        
        price = float(last["close"])
        atr_v = float(last.get("atr", 0))
        adx_v = float(last.get("adx", 0))
        
        # Vérifier régime haussier
        regime_ok = price > float(last.get("ema_trend", price))
        
        if not regime_ok:
            return Signal(HOLD, price, atr_v, "Regime non haussier")
        
        if adx_v < self.adx_min:
            return Signal(HOLD, price, atr_v, f"ADX {adx_v:.1f} < {self.adx_min}")
        
        if price > float(last.get("breakout_high", price)):
            return Signal(ENTER_LONG, price, atr_v, "Cassure Donchian")
        
        return Signal(HOLD, price, atr_v, "Pas de signal")
```

---

### 5. Module `core.risk`

**Rôle** : Gérer le risque et l'exposition.

**Architecture** :
```
risk/
├── stop_manager.py         # Gestion des stops
├── exposure.py             # Pilotage exposition
├── portfolio.py            # Gestion portefeuille
├── position_sizing.py      # Calcul de taille
└── drawdown_manager.py     # Gestion drawdowns
```

**StopManager** (existant, à refactoriser) :
```python
@dataclass
class StopManager:
    """Gère le stop pour une position."""
    
    entry_price: float
    entry_atr: float
    highest_high: float = 0.0
    stop: float = 0.0
    breakeven_done: bool = False
    
    def update(self, bar_high: float, bar_close: float, current_atr: float) -> None:
        """Met à jour le stop après une nouvelle bougie."""
        # 1. Mettre à jour le plus haut
        self.highest_high = max(self.highest_high, bar_high)
        
        # 2. Vérifier breakeven
        if not self.breakeven_done:
            r_gain = (bar_close - self.entry_price) / self.initial_risk
            if r_gain >= breakeven_at_r:
                self.stop = max(self.stop, self.entry_price)
                self.breakeven_done = True
        
        # 3. Stop suiveur
        chandelier = self.highest_high - trailing_atr * current_atr
        self.stop = max(self.stop, chandelier)
    
    def hit(self, bar_low: float) -> bool:
        """Le stop a-t-il été touché ?"""
        return bar_low <= self.stop
```

---

### 6. Module `core.execution`

**Rôle** : Exécuter les ordres sur les exchanges.

**Architecture** :
```
execution/
├── broker.py              # Broker ABC
├── paper_broker.py        # Simulation
├── live_broker.py          # Base pour live
└── exchanges/
    ├── base.py            # ExchangeBroker ABC
    ├── coinbase.py        # Coinbase
    ├── binance.py         # Binance
    └── kraken.py          # Kraken
```

**Broker Interface** :
```python
from abc import ABC, abstractmethod
from mistral_vibe_crypto.core.types import Order, Fill, Position

class Broker(ABC):
    """Interface pour un courtier."""
    
    @abstractmethod
    def get_cash(self) -> float:
        pass
    
    @abstractmethod
    def get_position(self, product_id: ProductId) -> Position:
        pass
    
    @abstractmethod
    def buy(self, order: Order) -> Fill:
        pass
    
    @abstractmethod
    def sell(self, order: Order) -> Fill:
        pass
    
    @abstractmethod
    def cancel(self, order_id: str) -> bool:
        pass
```

---

### 7. Module `core.backtesting`

**Rôle** : Effectuer des tests historiques.

**Architecture** :
```
backtesting/
├── engine.py               # Moteur de backtest
├── walkforward.py          # Walk-forward validation
├── montecarlo.py           # Simulation Monte Carlo
├── metrics.py              # Calcul des métriques
└── reporter.py             # Génération de rapports
```

**BacktestEngine** :
```python
class BacktestEngine:
    def __init__(
        self,
        strategy: Strategy,
        data_provider: DataProvider,
        initial_capital: float = 10000.0,
    ):
        self.strategy = strategy
        self.data_provider = data_provider
        self.initial_capital = initial_capital
    
    def run(
        self,
        product_id: ProductId,
        granularity: GranularityEnum,
        start_date: datetime,
        end_date: datetime,
    ) -> BacktestResult:
        # 1. Récupérer les données
        df = self.data_provider.get_candles(
            product_id, granularity, n_bars
        )
        
        # 2. Filtrer la période
        df = df.loc[start_date:end_date]
        
        # 3. Exécuter le backtest
        result = self._run_backtest(df, product_id)
        
        return result
    
    def _run_backtest(self, df: pd.DataFrame, product_id: ProductId) -> BacktestResult:
        # Implémentation du backtest barre par barre
        pass
```

---

## 🔄 Flux de Données

### 1. Flux Principal (Live Trading)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Exchange   │────▶│ DataProvider │────▶│   Strategy   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                              │
                                              ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Strategy   │────▶│    Signal    │────▶│ Risk Manager │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                              │
                                              ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Risk Manager │────▶│   Position   │────▶│    Broker    │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                              │
                                              ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Broker    │────▶│   Exchange   │────▶│   Fill      │
└─────────────┘     └─────────────┘     └─────────────┘
```

### 2. Flux de Backtesting

```
┌─────────────┐     ┌─────────────┐
│   DataProvider │────▶│   Backtest   │
└─────────────┘     │   Engine     │
                     └──────┬──────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                   Simulation Barre par Barre                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Strategy   │◀──▶│  PaperBroker │◀──▶│   Position   │  │
│  └─────────────┘    └─────────────┘    └─────────────┘  │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
                     ┌─────────────┐
                     │  Result      │
                     │ (Metrics,    │
                     │  Trades,     │
                     │  Equity)     │
                     └─────────────┘
```

---

## 🛡️ Gestion des Erreurs

### 1. Hiérarchie des Exceptions

```python
class CryptoTradingError(Exception):
    """Exception de base pour la plateforme."""
    pass

class DataError(CryptoTradingError):
    """Erreur liée aux données."""
    pass

class ProviderError(DataError):
    """Erreur de provider."""
    pass

class InsufficientDataError(DataError):
    """Données insuffisantes."""
    pass

class ExchangeError(CryptoTradingError):
    """Erreur liée à un exchange."""
    pass

class APIError(ExchangeError):
    """Erreur d'API."""
    pass

class RateLimitError(APIError):
    """Rate limit atteint."""
    pass

class AuthenticationError(APIError):
    """Erreur d'authentification."""
    pass

class OrderError(CryptoTradingError):
    """Erreur liée à un ordre."""
    pass

class OrderNotFilledError(OrderError):
    """Ordre non rempli."""
    pass

class InsufficientBalanceError(OrderError):
    """Solde insuffisant."""
    pass

class StrategyError(CryptoTradingError):
    """Erreur de stratégie."""
    pass

class RiskError(CryptoTradingError):
    """Erreur de gestion du risque."""
    pass

class MaxDrawdownError(RiskError):
    """Drawdown maximal atteint."""
    pass

class DailyLossError(RiskError):
    """Perte journalière maximale atteinte."""
    pass
```

### 2. Gestion des Erreurs dans l'Engine

```python
class Engine:
    def tick(self) -> None:
        try:
            # Exécution normale
            self._execute_tick()
        except InsufficientDataError as e:
            logger.warning(f"Données insuffisantes: {e}")
            # Attendre et réessayer
        except ProviderError as e:
            logger.error(f"Erreur provider: {e}")
            # Changer de provider ou notifier
        except RateLimitError as e:
            logger.warning(f"Rate limit: {e}")
            # Attendre et réessayer
        except MaxDrawdownError as e:
            logger.error(f"Max drawdown atteint: {e}")
            # Arrêter le bot et notifier
            self._stop_bot()
            self._notify_emergency()
        except Exception as e:
            logger.exception(f"Erreur inattendue: {e}")
            # Notifier mais continuer
            self._notify_error(e)
```

---

## 📊 Configuration

### 1. Structure de Configuration

```yaml
# Configuration globale
app:
  name: mistral-vibe-crypto
  version: 0.1.0
  environment: production  # development | staging | production
  log_level: INFO

# Exchanges
api_keys:
  coinbase:
    key: ${COINBASE_API_KEY}
    secret: ${COINBASE_API_SECRET}
  binance:
    key: ${BINANCE_API_KEY}
    secret: ${BINANCE_API_SECRET}

# Default Data Provider
data:
  default_provider: coinbase
  cache:
    enabled: true
    type: redis  # memory | redis
    ttl: 3600  # secondes

# Default Exchange for Trading
execution:
  default_exchange: coinbase
  default_broker: paper  # paper | live

# Notifications
notifications:
  telegram:
    enabled: false
    bot_token: ${TELEGRAM_BOT_TOKEN}
    chat_id: ${TELEGRAM_CHAT_ID}
  email:
    enabled: false
    # ...
```

### 2. Gestion des Secrets

**Ne jamais commiter les secrets** !

Utiliser :
- Fichier `.env` (exclu par `.gitignore`)
- Variables d'environnement
- Service de secrets (Vault, AWS Secrets Manager)

---

## 🚀 Déploiement

### 1. Environnements

| Environnement | Usage | Configuration |
|---------------|-------|---------------|
| Development | Développement local | `config.dev.yaml` |
| Staging | Tests pré-production | `config.staging.yaml` |
| Production | Production | `config.prod.yaml` |

### 2. Conteneurisation

**Dockerfile** :
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers
COPY requirements.txt .
COPY . .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Installer la librairie en mode editable
RUN pip install --no-cache-dir -e .

# Configurer l'utilisateur
RUN useradd -m mistral
USER mistral

# Commande par défaut
CMD ["python", "-m", "bots.swing_bot", "paper"]
```

**docker-compose.yml** :
```yaml
version: '3.8'

services:
  app:
    build: .
    environment:
      - ENVIRONMENT=production
      - COINBASE_API_KEY=${COINBASE_API_KEY}
      - COINBASE_API_SECRET=${COINBASE_API_SECRET}
    volumes:
      - ./config.prod.yaml:/app/config.yaml
      - ./state:/app/state
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped

volumes:
  redis_data:
  grafana_data:
```

### 3. Orchestration (Kubernetes)

Pour les déploiements à grande échelle :
- Déployer chaque bot comme un pod
- Utiliser des ConfigMaps pour la configuration
- Utiliser des Secrets pour les clés API
- Mettre en place des liveness/readiness probes
- Configurer le scaling horizontal

---

## 📈 Monitoring

### 1. Métriques (Prometheus)

**Métriques clés à suivre** :

```python
# Equity
BOT_EQUITY = Gauge('bot_equity', 'Current equity', ['bot_id', 'strategy', 'product_id'])
BOT_EQUITY_PEAK = Gauge('bot_equity_peak', 'Peak equity', ['bot_id', 'strategy'])

# Drawdown
BOT_DRAWDOWN = Gauge('bot_drawdown_pct', 'Current drawdown %', ['bot_id'])
BOT_MAX_DRAWDOWN = Gauge('bot_max_drawdown_pct', 'Max drawdown %', ['bot_id'])

# Trades
BOT_TRADES_TOTAL = Counter('bot_trades_total', 'Total trades', ['bot_id', 'side', 'product_id'])
BOT_TRADES_WINNING = Counter('bot_trades_winning', 'Winning trades', ['bot_id'])
BOT_TRADES_LOSING = Counter('bot_trades_losing', 'Losing trades', ['bot_id'])
BOT_PNL_TOTAL = Gauge('bot_pnl_total', 'Total PnL', ['bot_id'])

# Performance
BOT_WIN_RATE = Gauge('bot_win_rate', 'Win rate %', ['bot_id'])
BOT_PROFIT_FACTOR = Gauge('bot_profit_factor', 'Profit factor', ['bot_id'])
BOT_SHARPE_RATIO = Gauge('bot_sharpe_ratio', 'Sharpe ratio', ['bot_id'])

# Exécution
BOT_ORDER_LATENCY = Histogram('bot_order_latency_seconds', 'Order latency', ['bot_id', 'exchange'])
BOT_SLIPPAGE = Gauge('bot_slippage_bps', 'Slippage in bps', ['bot_id'])
BOT_FEE_TOTAL = Gauge('bot_fee_total', 'Total fees paid', ['bot_id'])

# Système
BOT_UPTIME = Gauge('bot_uptime_seconds', 'Bot uptime', ['bot_id'])
BOT_ERRORS = Counter('bot_errors_total', 'Total errors', ['bot_id', 'error_type'])
```

### 2. Dashboards (Grafana)

**Dashboards recommandés** :

1. **Overview** : Vue d'ensemble de tous les bots
2. **Performance** : Métriques de performance (PnL, drawdown, etc.)
3. **Execution** : Latence, slippage, frais
4. **System** : Santé du système (CPU, mémoire, erreurs)
5. **Per Bot** : Dashboard dédié par bot

---

## 🔒 Sécurité

### 1. Bonnes Pratiques

1. **Ne jamais stocker de secrets en clair**
   - Utiliser `.env` + `.gitignore`
   - Utiliser des services de secrets (Vault, AWS Secrets Manager)
   - Encrypter les fichiers sensibles

2. **Principle of Least Privilege**
   - Donner uniquement les permissions nécessaires
   - Séparer les clés par environnement
   - Limiter les accès en lecture/écriture

3. **Rotation des Clés**
   - Changer les clés API régulièrement
   - Utiliser des clés temporaires pour les tests
   - Révoquer les clés compromis

4. **Audit et Logging**
   - Logger toutes les actions sensibles
   - Conserver les logs pendant 6-12 mois
   - Mettre en place des alertes de sécurité

### 2. Implémentation de la Sécurité

```python
# Exemple : Masquage des secrets dans les logs
import logging
import os

SENSITIVE_KEYS = ['api_key', 'secret', 'token', 'password', 'private']

class SecureFormatter(logging.Formatter):
    def format(self, record):
        message = super().format(record)
        for key in SENSITIVE_KEYS:
            message = message.replace(key, '[REDACTED]')
        return message

# Configuration du logger
logger = logging.getLogger('bot')
logger.setLevel(logging.INFO)

# Appliquer le formatter sécurisé
handler = logging.StreamHandler()
handler.setFormatter(SecureFormatter())
logger.addHandler(handler)
```

---

## 📚 Documentation Additionnelle

### 1. API Documentation

Voir [`docs/API.md`](./API.md) pour la documentation complète de l'API.

### 2. Development Guide

Voir [`docs/DEVELOPMENT.md`](./DEVELOPMENT.md) pour le guide de développement.

### 3. Deployment Guide

Voir [`docs/DEPLOYMENT.md`](./DEPLOYMENT.md) pour le guide de déploiement.

### 4. Examples

Voir [`docs/EXAMPLES.md`](./EXAMPLES.md) pour des exemples d'utilisation.

---

## 🎯 Résumé

L'architecture de **Mistral Vibe Crypto** est conçue pour être :

✅ **Modulaire** : Chaque composant est indépendant
✅ **Extensible** : Facile d'ajouter de nouvelles stratégies, exchanges, etc.
✅ **Maintenable** : Code propre, bien organisé, bien documenté
✅ **Testable** : Tests unitaires et d'intégration
✅ **Production-Ready** : Monitoring, logging, gestion des erreurs
✅ **Sécurisée** : Bonnes pratiques de sécurité intégrées

Cette architecture permet de **capitaliser sur l'existant** tout en **ouvrant la voie à de nouvelles fonctionnalités** (multi-exchange, portfolio management, ML, etc.).

---

## 📞 Support

Pour toute question sur l'architecture :
- Consulter les documents dans `docs/`
- Contacter l'équipe de développement
- Ouvrir une issue GitHub

---

> **💡 Note** : Cette architecture est **évolutive**. Elle peut être adaptée et améliorée en fonction des besoins spécifiques et des retours d'expérience.
