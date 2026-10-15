# Plan d'Action Immédiat - Mistral Vibe Crypto

## Contexte
Suite à l'analyse du projet existant (`python-swing-bot`), ce document définit les **actions prioritaires à démarrer immédiatement** pour créer la base `mistral-vibe-crypto`.

---

## 🎯 Objectif Phase 0 (Cette Semaine)
**Créer la structure de base de `mistral-vibe-crypto` et commencer le refactoring du code existant.**

---

## Tâches Prioritaires

### Jour 1 : Setup & Préparation

#### 1.1. Initialisation du Projet
```bash
# Créer la structure de base
mkdir -p mistral-vibe-crypto/{core/{indicators,data/{providers,cache},strategies,risk,execution,backtesting,utils},bots/{swing-bot},tests,docs}

# Créer les fichiers de base
Touch mistral-vibe-crypto/{README.md,.gitignore,setup.py,requirements.txt,pyproject.toml}
```

#### 1.2. Fichiers de Configuration
- [ ] `requirements.txt` : Liste des dépendances
- [ ] `pyproject.toml` : Configuration du package Python
- [ ] `setup.py` : Script d'installation
- [ ] `.gitignore` : Exclusions Git

**Contenu `requirements.txt`** :
```
pandas>=2.0
numpy>=1.24
PyYAML>=6.0
python-dotenv>=1.0
requests>=2.31
matplotlib>=3.7
coinbase-advanced-py>=1.7.0
redis>=4.0
```

**Contenu `pyproject.toml`** :
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "mistral-vibe-crypto"
version = "0.1.0"
description = "Mistral Vibe Crypto Trading Platform"
readme = "README.md"
requires-python = ">=3.12"
license = {text = "MIT"}
authors = [
    {name = "Mistral Vibe Team", email = "vibe@mistral.ai"}
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "mypy>=1.0",
    "ruff>=0.1",
    "jupyter>=1.0",
]
```

#### 1.3. Documentation Initiale
- [ ] `mistral-vibe-crypto/README.md` : Documentation principale
- [ ] `mistral-vibe-crypto/docs/ARCHITECTURE.md` : Architecture cible

---

### Jour 2 : Types et Utilitaires Communs

#### 2.1. Types Communs (`core/types.py`)
Créer les types de base utilisés dans toute la plateforme.

```python
"""Types communs pour la plateforme Mistral Vibe Crypto."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd


# --- Enums ---

class ExchangeEnum(Enum):
    """Exchanges supportés."""
    COINBASE = "coinbase"
    BINANCE = "binance"
    KRAKEN = "kraken"
    BYBIT = "bybit"


class GranularityEnum(Enum):
    """Granularités (timeframes) supportées."""
    ONE_MINUTE = "ONE_MINUTE"
    FIVE_MINUTE = "FIVE_MINUTE"
    FIFTEEN_MINUTE = "FIFTEEN_MINUTE"
    THIRTY_MINUTE = "THIRTY_MINUTE"
    ONE_HOUR = "ONE_HOUR"
    TWO_HOUR = "TWO_HOUR"
    SIX_HOUR = "SIX_HOUR"
    ONE_DAY = "ONE_DAY"
    
    @property
    def seconds(self) -> int:
        """Retourne la granularité en secondes."""
        mapping = {
            self.ONE_MINUTE: 60,
            self.FIVE_MINUTE: 300,
            self.FIFTEEN_MINUTE: 900,
            self.THIRTY_MINUTE: 1800,
            self.ONE_HOUR: 3600,
            self.TWO_HOUR: 7200,
            self.SIX_HOUR: 21600,
            self.ONE_DAY: 86400,
        }
        return mapping[self]


class OrderTypeEnum(Enum):
    """Types d'ordres."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSideEnum(Enum):
    """Sides d'ordre."""
    BUY = "BUY"
    SELL = "SELL"


class LiquidityEnum(Enum):
    """Type de liquidité."""
    MAKER = "maker"
    TAKER = "taker"


class SignalActionEnum(Enum):
    """Actions de signal."""
    HOLD = "hold"
    ENTER_LONG = "enter_long"
    EXIT_LONG = "exit_long"
    ENTER_SHORT = "enter_short"
    EXIT_SHORT = "exit_short"


# --- Data Classes ---

@dataclass
class Candle:
    """Représente une bougie OHLCV."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    @classmethod
    def from_series(cls, series: pd.Series) -> "Candle":
        """Crée une Candle à partir d'une Series pandas."""
        return cls(
            timestamp=series.name,
            open=float(series["open"]),
            high=float(series["high"]),
            low=float(series["low"]),
            close=float(series["close"]),
            volume=float(series["volume"]),
        )
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


@dataclass
class Order:
    """Représente un ordre à passer."""
    side: OrderSideEnum
    order_type: OrderTypeEnum
    quantity: float
    product_id: str
    price: Optional[float] = None
    stop_price: Optional[float] = None
    post_only: bool = False
    reduce_only: bool = False
    client_order_id: Optional[str] = None


@dataclass
class Fill:
    """Représente un fill (exécution d'ordre)."""
    order_id: str
    side: OrderSideEnum
    quantity: float
    filled_quantity: float
    price: float
    average_filled_price: float
    fee: float
    fee_currency: str
    liquidity: LiquidityEnum
    timestamp: datetime
    
    @property
    def is_complete(self) -> bool:
        """L'ordre est-il complètement rempli ?"""
        return abs(self.filled_quantity - self.quantity) < 1e-12


@dataclass
class Position:
    """Représente une position."""
    product_id: str
    quantity: float
    average_price: float
    side: OrderSideEnum  # BUY = long, SELL = short
    entry_timestamp: datetime
    
    @property
    def is_long(self) -> bool:
        """Position longue ?"""
        return self.side == OrderSideEnum.BUY
    
    @property
    def is_short(self) -> bool:
        """Position courte ?"""
        return self.side == OrderSideEnum.SELL
    
    @property
    def is_open(self) -> bool:
        """Position ouverte ?"""
        return abs(self.quantity) > 1e-12
    
    def value(self, mark_price: float) -> float:
        """Valeur de la position au prix mark."""
        if self.is_long:
            return self.quantity * mark_price
        else:
            return -self.quantity * mark_price  # Short: valeur négative


@dataclass
class Signal:
    """Représente un signal de trading."""
    action: SignalActionEnum
    price: float
    atr: float
    reason: str
    regime_ok: bool = False
    adx: float = 0.0
    confidence: float = 0.0
    
    @property
    def is_enter(self) -> bool:
        """Signal d'entrée ?"""
        return self.action in (SignalActionEnum.ENTER_LONG, SignalActionEnum.ENTER_SHORT)
    
    @property
    def is_exit(self) -> bool:
        """Signal de sortie ?"""
        return self.action in (SignalActionEnum.EXIT_LONG, SignalActionEnum.EXIT_SHORT)


@dataclass
class Trade:
    """Représente un trade (entrée + sortie)."""
    entry_time: datetime
    exit_time: datetime
    product_id: str
    entry_price: float
    exit_price: float
    quantity: float
    entry_fee: float
    exit_fee: float
    side: OrderSideEnum
    pnl: float
    r_multiple: float
    reason: str
    
    @property
    def is_profitable(self) -> bool:
        """Trade profitable ?"""
        return self.pnl > 0


# --- Type Aliases ---

ProductId = str  # Format: BASE-QUOTE (ex: "BTC-USDC")
Currency = str  # Format: ISO code (ex: "BTC", "USDC")
Timestamp = datetime
Price = float
Quantity = float
Equity = float
```

#### 2.2. Utilitaires Communs (`core/utils/`)

**Fichiers à créer** :
- `core/utils/__init__.py`
- `core/utils/config.py` : Gestion configuration
- `core/utils/logging.py` : Configuration logging
- `core/utils/validators.py` : Validateurs de données
- `core/utils/helpers.py` : Fonctions utilitaires

**Exemple `core/utils/config.py`** :
```python
"""Gestion centralisée de la configuration."""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv


class ConfigLoader:
    """Chargeur de configuration."""
    
    def __init__(self, config_path: Optional[str] = None, env_path: Optional[str] = None):
        self.config_path = config_path or "config.yaml"
        self.env_path = env_path or ".env"
        self._config: Optional[dict] = None
        
    def load(self) -> dict:
        """Charge la configuration depuis les fichiers."""
        if self._config is not None:
            return self._config
            
        # Charger les variables d'environnement
        load_dotenv(self.env_path)
        
        # Charger le fichier YAML
        config_path = Path(self.config_path)
        if config_path.exists():
            with open(config_path) as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = {}
        
        # Ajouter les variables d'environnement
        self._add_env_vars()
        
        return self._config
    
    def _add_env_vars(self) -> None:
        """Ajoute les variables d'environnement à la config."""
        if self._config is None:
            self._config = {}
            
        # Mapping des variables d'environnement
        env_mapping = {
            "COINBASE_API_KEY": "api_keys.coinbase.key",
            "COINBASE_API_SECRET": "api_keys.coinbase.secret",
            "BINANCE_API_KEY": "api_keys.binance.key",
            "BINANCE_API_SECRET": "api_keys.binance.secret",
            "TELEGRAM_BOT_TOKEN": "notifications.telegram.token",
            "TELEGRAM_CHAT_ID": "notifications.telegram.chat_id",
        }
        
        for env_var, config_path in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                # Créer les clés intermédiaires si nécessaire
                keys = config_path.split(".")
                current = self._config
                for key in keys[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                current[keys[-1]] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Récupère une valeur de configuration."""
        config = self.load()
        keys = key.split(".")
        current = config
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current
```

---

### Jour 3 : Module Indicateurs Techniques

#### 3.1. Refactor de `indicators.py`
Copier et adapter le code existant dans `core/indicators/` avec une meilleure organisation.

**Structure** :
```
core/indicators/
├── __init__.py          # Exports publics
├── base.py              # Classes de base
├── trend.py             # Indicateurs de tendance (EMA, SMA, etc.)
├── volatility.py        # Indicateurs de volatilité (ATR, etc.)
├── momentum.py          # Indicateurs de momentum (RSI, MACD, etc.)
├── volume.py            # Indicateurs de volume
└── patterns.py          # Patterns (Donchian, etc.)
```

**Contenu `core/indicators/__init__.py`** :
```python
"""Module indicateurs techniques."""

from .base import Indicator, IndicatorConfig
from .trend import ema, sma, slope
from .volatility import atr, true_range
from .momentum import adx, rsi, macd, stochastic
from .volume import volume_sma, obv
from .patterns import donchian_high, donchian_low

__all__ = [
    "Indicator",
    "IndicatorConfig",
    "ema",
    "sma",
    "slope",
    "atr",
    "true_range",
    "adx",
    "rsi",
    "macd",
    "stochastic",
    "volume_sma",
    "obv",
    "donchian_high",
    "donchian_low",
]
```

**Contenu `core/indicators/base.py`** :
```python
"""Classes de base pour les indicateurs."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class IndicatorConfig:
    """Configuration d'un indicateur."""
    name: str
    period: int
    parameters: Optional[dict] = None


class Indicator(ABC):
    """Interface de base pour un indicateur."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nom de l'indicateur."""
        pass
    
    @property
    @abstractmethod
    def required_columns(self) -> list[str]:
        """Colonnes requises dans le DataFrame."""
        pass
    
    @abstractmethod
    def compute(self, df: pd.DataFrame, **kwargs) -> pd.Series:
        """Calcule l'indicateur sur le DataFrame."""
        pass
```

**Contenu `core/indicators/trend.py`** :
```python
"""Indicateurs de tendance."""

import pandas as pd


def ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=span, adjust=False).mean()


def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window).mean()


def slope(series: pd.Series, lookback: int) -> pd.Series:
    """Pente moyenne sur lookback périodes."""
    return (series - series.shift(lookback)) / lookback
```

---

### Jour 4 : Module Data Providers

#### 4.1. Structure de Base
```
core/data/
├── __init__.py
├── providers/
│   ├── __init__.py
│   ├── base.py          # DataProvider ABC
│   ├── coinbase.py      # Refactored Coinbase
│   ├── binance.py       # Nouveau
│   └── kraken.py        # Nouveau
├── cache/
│   ├── __init__.py
│   ├── base.py          # Cache ABC
│   └── redis_cache.py   # Implémentation Redis
└── factory.py           # Factory de providers
```

#### 4.2. Interface DataProvider (`core/data/providers/base.py`)

```python
"""Interface de base pour les providers de données."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

import pandas as pd

from mistral_vibe_crypto.core.types import GranularityEnum, ProductId


class DataProvider(ABC):
    """Interface pour un provider de données marché."""
    
    def __init__(self, cache_enabled: bool = False):
        self.cache_enabled = cache_enabled
        self._cache: dict = {}
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nom du provider."""
        pass
    
    @property
    @abstractmethod
    def supported_granularities(self) -> list[GranularityEnum]:
        """Granularités supportées."""
        pass
    
    @abstractmethod
    def get_candles(
        self,
        product_id: ProductId,
        granularity: GranularityEnum,
        n_bars: int,
    ) -> pd.DataFrame:
        """Récupère les n_bars dernières bougies.
        
        Args:
            product_id: Identifiant du produit (ex: "BTC-USDC")
            granularity: Granularité
            n_bars: Nombre de bougies
            
        Returns:
            DataFrame avec index datetime et colonnes ohlcv
        """
        pass
    
    @abstractmethod
    def get_spot_price(self, product_id: ProductId) -> float:
        """Récupère le prix spot actuel."""
        pass
    
    @abstractmethod
    def get_orderbook(self, product_id: ProductId, depth: int = 10) -> dict:
        """Récupère le orderbook."""
        pass
    
    @abstractmethod
    def get_ticker(self, product_id: ProductId) -> dict:
        """Récupère le ticker (24h stats)."""
        pass
    
    @abstractmethod
    def get_products(self) -> list[dict]:
        """Liste tous les produits disponibles."""
        pass
    
    def clear_cache(self) -> None:
        """Efface le cache."""
        self._cache = {}
```

#### 4.3. Implémentation Coinbase (`core/data/providers/coinbase.py`)

```python
"""Provider Coinbase."""

import time
from typing import Optional

import pandas as pd
import requests

from mistral_vibe_crypto.core.data.providers.base import DataProvider
from mistral_vibe_crypto.core.types import GranularityEnum, ProductId


class CoinbaseProvider(DataProvider):
    """Provider de données pour Coinbase Advanced Trade."""
    
    PUBLIC_BASE = "https://api.coinbase.com/api/v3/brokerage/market"
    MAX_CANDLES_PER_REQ = 300
    
    def __init__(self, cache_enabled: bool = False):
        super().__init__(cache_enabled)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "mistral-vibe-crypto/0.1"})
    
    @property
    def name(self) -> str:
        return "coinbase"
    
    @property
    def supported_granularities(self) -> list[GranularityEnum]:
        return list(GranularityEnum)
    
    def _get_json(self, url: str, params: dict) -> dict:
        """Effectue une requête GET avec retry."""
        for attempt in range(4):
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (429, 500, 502, 503):
                time.sleep(1.5 * (attempt + 1))
                continue
            resp.raise_for_status()
        resp.raise_for_status()
        return {}
    
    def get_candles(
        self,
        product_id: ProductId,
        granularity: GranularityEnum,
        n_bars: int,
    ) -> pd.DataFrame:
        """Récupère les bougies depuis Coinbase."""
        cache_key = (product_id, granularity.value)
        if self.cache_enabled and cache_key in self._cache:
            cached = self._cache[cache_key]
            if len(cached) >= n_bars:
                return cached.tail(n_bars).copy()
        
        rows: list[dict] = []
        remaining = n_bars
        cursor_end = int(time.time())
        granularity_seconds = granularity.seconds
        empty_streak = 0
        max_calls = n_bars // self.MAX_CANDLES_PER_REQ + 5
        
        for _ in range(max_calls):
            if remaining <= 0:
                break
            span = min(remaining, self.MAX_CANDLES_PER_REQ)
            start = cursor_end - span * granularity_seconds
            data = self._get_json(
                f"{self.PUBLIC_BASE}/products/{product_id}/candles",
                {"start": str(start), "end": str(cursor_end), "granularity": granularity.value},
            )
            batch = data.get("candles", [])
            if batch:
                rows.extend(batch)
                remaining -= len(batch)
                empty_streak = 0
            else:
                empty_streak += 1
                if empty_streak >= 3:
                    break
            cursor_end = start
            time.sleep(0.2)
        
        if not rows:
            raise RuntimeError(f"Aucune bougie renvoyée pour {product_id}")
        
        df = pd.DataFrame(rows)
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["time"] = pd.to_datetime(pd.to_numeric(df["start"]), unit="s", utc=True)
        df = (
            df.drop(columns=["start"])
            .drop_duplicates(subset="time")
            .set_index("time")
            .sort_index()[["open", "high", "low", "close", "volume"]]
        )
        
        if self.cache_enabled:
            self._cache[cache_key] = df
            
        return df.tail(n_bars)
    
    def get_spot_price(self, product_id: ProductId) -> float:
        data = self._get_json(f"{self.PUBLIC_BASE}/products/{product_id}", {})
        return float(data["price"])
    
    def get_orderbook(self, product_id: ProductId, depth: int = 10) -> dict:
        # Coinbase Advanced Trade ne fournit pas de orderbook complet
        # Retourner une approximation
        return {"bids": [], "asks": []}
    
    def get_ticker(self, product_id: ProductId) -> dict:
        data = self._get_json(f"{self.PUBLIC_BASE}/products/{product_id}", {})
        return {
            "price": float(data.get("price", 0)),
            "price_percent_change_24h": float(data.get("price_percent_change_24h", 0)),
            "volume_24h": float(data.get("volume_24h", 0)),
        }
    
    def get_products(self) -> list[dict]:
        data = self._get_json(f"{self.PUBLIC_BASE}/products", {})
        return data.get("products", [])
```

#### 4.4. Factory de Providers (`core/data/factory.py`)

```python
"""Factory pour les providers de données."""

from mistral_vibe_crypto.core.data.providers.base import DataProvider
from mistral_vibe_crypto.core.data.providers.coinbase import CoinbaseProvider
from mistral_vibe_crypto.core.types import ExchangeEnum


class DataProviderFactory:
    """Factory pour créer des providers de données."""
    
    _providers: dict[ExchangeEnum, type[DataProvider]] = {
        ExchangeEnum.COINBASE: CoinbaseProvider,
        # ExchangeEnum.BINANCE: BinanceProvider,  # À implémenter
        # ExchangeEnum.KRAKEN: KrakenProvider,   # À implémenter
    }
    
    @classmethod
    def create(
        cls,
        exchange: ExchangeEnum,
        cache_enabled: bool = False,
    ) -> DataProvider:
        """Crée un provider pour l'exchange spécifié."""
        provider_class = cls._providers.get(exchange)
        if provider_class is None:
            raise ValueError(f"Exchange {exchange.value} non supporté")
        return provider_class(cache_enabled=cache_enabled)
    
    @classmethod
    def get_supported_exchanges(cls) -> list[ExchangeEnum]:
        """Liste des exchanges supportés."""
        return list(cls._providers.keys())
```

---

### Jour 5 : Intégration et Tests

#### 5.1. Migration du Bot Existant
- [ ] Adapter `python-swing-bot/bot/` pour utiliser les nouveaux modules
- [ ] Conserver la rétrocompatibilité
- [ ] Tests de non-régression

#### 5.2. Tests Unitaires
- [ ] Tests pour `types.py`
- [ ] Tests pour `utils/`
- [ ] Tests pour `indicators/`
- [ ] Tests pour `data/providers/`

**Exemple de test** (`tests/test_indicators.py`) :
```python
"""Tests pour les indicateurs techniques."""

import pandas as pd
import pytest

from mistral_vibe_crypto.core.indicators import ema, sma, atr, rsi


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Données de test."""
    data = {
        "open": [100, 101, 102, 103, 104],
        "high": [101, 102, 103, 104, 105],
        "low": [99, 100, 101, 102, 103],
        "close": [100.5, 101.5, 102.5, 103.5, 104.5],
        "volume": [1000, 2000, 1500, 3000, 2500],
    }
    return pd.DataFrame(data)


def test_ema(sample_data):
    """Test EMA."""
    result = ema(sample_data["close"], 3)
    assert len(result) == len(sample_data)
    assert result.iloc[0] != result.iloc[0]  # NaN pour la première
    assert result.iloc[2] == pytest.approx(101.5, rel=1e-5)


def test_atr(sample_data):
    """Test ATR."""
    result = atr(sample_data["high"], sample_data["low"], sample_data["close"], 14)
    assert len(result) == len(sample_data)
    assert not result.iloc[0] == result.iloc[0]  # NaN


def test_rsi(sample_data):
    """Test RSI."""
    result = rsi(sample_data["close"], 14)
    assert len(result) == len(sample_data)
    assert result.iloc[-1] != 0  # Pas zéro si mouvement
```

---

## Résumé de la Semaine

| Jour | Focus | Livrables |
|------|-------|-----------|
| 1 | Setup, Config | Structure projet, requirements, pyproject.toml |
| 2 | Types & Utils | types.py, utils/, logging |
| 3 | Indicateurs | Module indicators/ complet |
| 4 | Data Providers | Module data/ avec Coinbase |
| 5 | Intégration | Tests, adaptation du bot existant |

---

## Prochaines Étapes (Semaine 2)

1. **Compléter Phase 1** :
   - [ ] Module `strategies/`
   - [ ] Module `risk/`
   - [ ] Module `execution/`
   - [ ] Module `backtesting/`

2. **Ajouter Binance Provider** :
   - [ ] Implémenter `BinanceProvider`
   - [ ] Tests pour Binance

3. **Portfolio Management** :
   - [ ] Classe Portfolio
   - [ ] Allocation dynamique

---

## Blockers Potentiels & Solutions

### 1. Complexité du Refactoring
**Problème** : Le code existant est bien intégré, le refactoring peut casser des choses.
**Solution** : 
- Commencer par les modules les moins couplés (indicators, types)
- Maintenir la rétrocompatibilité
- Tests de non-régression à chaque étape
- Utiliser des feature flags pour basculer entre ancien/nouveau

### 2. Manque de Connaissances sur Coinbase API
**Problème** : L'API Coinbase a des particularités.
**Solution** : 
- Étudier la documentation officielle
- Analyser le code existant (`coinbase_client.py`)
- Faire des tests avec des clés sandbox
- Documenter les limitations

### 3. Temps Limité
**Problème** : Beaucoup de travail pour une petite équipe.
**Solution** : 
- Prioriser les tâches (refactoring > nouvelles fonctionnalités)
- Faire du code simple et maintenable
- Éviter la sur-ingénierie
- Itérer rapidement

---

## Ressources Utiles

### Documentation
- [Coinbase Advanced Trade API](https://docs.cloud.coinbase.com/advanced-trade-api/docs/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [Python typing](https://docs.python.org/3/library/typing.html)
- [Dataclasses](https://docs.python.org/3/library/dataclasses.html)

### Outils
- [PyCharm](https://www.jetbrains.com/pycharm/) : IDE recommandé
- [VSCode](https://code.visualstudio.com/) : Alternative
- [Git](https://git-scm.com/) : Version control
- [GitHub](https://github.com/) : Hébergement du code

### Librairies Utiles
- [CCXT](https://github.com/ccxt/ccxt) : Alternative pour multi-exchange
- [Backtrader](https://www.backtrader.com/) : Framework backtesting
- [Freqtrade](https://github.com/freqtrade/freqtrade) : Plateforme open-source
- [TA-Lib](https://github.com/mrjbq7/ta-lib) : Librairie indicateurs C++

---

## Contact & Support

Pour toute question ou problème, contacter :
- **Email** : vibe@mistral.ai
- **Slack** : #crypto-trading (à créer)
- **GitHub** : mistral-ai/mistral-vibe-crypto (à créer)
