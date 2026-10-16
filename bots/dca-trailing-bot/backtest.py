"""Backtest pour le DCA Trailing Bot.

Moteur de backtest complet avec :
- Simulation des entrées DCA
- Gestion du trailing stop
- Calcul du PnL
- Métriques détaillées
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

import numpy as np
import pandas as pd
from dateutil import parser

# Ajouter le dossier courant au path
sys.path.insert(0, str(Path(__file__).parent))

from config import BotConfig
from strategy import DCATrailingStrategy, DCAState, Signal, HOLD, ENTER_LONG, DCA_ENTER, EXIT, TAKE_PROFIT
from coinbase_client import MarketData
from indicators import atr as calc_atr

log = logging.getLogger("dca_trailing_bot.backtest")


@dataclass
class Trade:
    """Représente un trade."""
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float] = None
    quantity: float = 0.0
    entry_fee: float = 0.0
    exit_fee: float = 0.0
    pnl: float = 0.0
    r_multiple: float = 0.0
    reason: str = ""
    dca_level: int = 0  # 0 = entrée initiale, 1, 2, 3 = DCA
    is_dca: bool = False
    
    @property
    def is_open(self) -> bool:
        return self.exit_time is None
    
    @property
    def is_profitable(self) -> bool:
        return self.pnl > 0


@dataclass
class BacktestResult:
    """Résultat d'un backtest."""
    equity_curve: pd.Series
    trades: list[Trade] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    dca_entries: list[dict] = field(default_factory=list)  # Details des entrées DCA
    price_data: Optional[pd.DataFrame] = None  # Données de prix pour les graphiques
    
    def summary(self) -> str:
        """Génère un résumé textuel."""
        s = self.stats
        lines = [
            "=" * 60,
            "         RÉSULTAT BACKTEST - DCA TRAILING BOT",
            "=" * 60,
            f"Période              : {s.get('start', '?')} -> {s.get('end', '?')} ({s.get('days', 0):.0f} jours)",
            f"Capital initial      : ${s.get('start_equity', 0):,.2f}",
            f"Capital final        : ${s.get('end_equity', 0):,.2f}",
            f"Performance          : {s.get('total_return_pct', 0):+,.2f}%",
            f"CAGR                 : {s.get('cagr_pct', 0):+,.2f}%",
            f"Buy & Hold           : {s.get('buy_hold_pct', 0):+,.2f}%",
            f"Max Drawdown         : {s.get('max_drawdown_pct', 0):.2f}%",
            f"Sharpe (annualisé)   : {s.get('sharpe', 0):.2f}",
            "-" * 60,
            f"Nombre de trades     : {s.get('n_trades', 0)}",
            f"  - Avec DCA         : {s.get('n_dca_trades', 0)}",
            f"  - Complètes        : {s.get('n_complete_trades', 0)}",
            f"Taux de réussite      : {s.get('win_rate_pct', 0):.1f}%",
            f"Gain moyen           : ${s.get('avg_win', 0):+,.2f}",
            f"Perte moyenne        : ${s.get('avg_loss', 0):+,.2f}",
            f"R moyen              : {s.get('avg_r', 0):+,.2f}",
            f"Profit Factor        : {s.get('profit_factor', 0):.2f}",
            f"Gain max / trade     : ${s.get('max_win', 0):+,.2f}",
            f"Perte max / trade   : ${s.get('max_loss', 0):+,.2f}",
            "-" * 60,
            f"Temps en position    : {s.get('time_in_market_pct', 0):.1f}%",
            f"Coûts totaux        : ${s.get('total_fees', 0):,.2f}",
            f"Nombre de DCA       : {s.get('total_dca_entries', 0)}",
            "=" * 60,
        ]
        return "\n".join(lines)


@dataclass
class Position:
    """Représente une position en cours."""
    entry_time: datetime
    entry_price: float
    quantity: float = 0.0
    total_cost: float = 0.0  # Coût total (y compris DCA)
    avg_price: float = 0.0  # Prix moyen
    dca_level: int = 0
    entry_fees: float = 0.0
    
    def add_dca(self, price: float, qty: float, fee: float) -> None:
        """Ajoute une entrée DCA."""
        self.quantity += qty
        self.total_cost += qty * price + fee
        self.avg_price = self.total_cost / self.quantity
        self.entry_fees += fee
        self.dca_level += 1


class DCABacktester:
    """Moteur de backtest pour la stratégie DCA."""
    
    def __init__(
        self,
        config: BotConfig,
        market_data: Optional[MarketData] = None,
    ):
        self.config = config
        self.market_data = market_data or MarketData()
        self.strategy = self._create_strategy()
        
        # Configuration
        self.fees_bps = config.execution.limit_offset_bps * 2  # aller-retour
        self.slippage_bps = 2.0  # Par défaut
    
    # ------------------------------------------------------------------
    def _create_strategy(self) -> DCATrailingStrategy:
        """Crée la stratégie depuis la config."""
        return DCATrailingStrategy(
            entry_mode=self.config.strategy.entry_mode,
            initial_entry_condition=getattr(self.config.strategy, 'initial_entry_condition', 'donchian_breakout'),
            dca_levels=self.config.strategy.dca_levels,
            dca_percentage=self.config.strategy.dca_percentage,
            dca_delay_bars=self.config.strategy.dca_delay_bars,
            dca_pullback_levels=self.config.strategy.dca_pullback_levels,
            trailing_stop_pct=self.config.strategy.trailing_stop_percentage,
            initial_stop_pct=self.config.strategy.initial_stop_percentage,
            take_profit_r_multiple=self.config.strategy.take_profit_r_multiple,
            trend_ema=self.config.strategy.trend_ema,
            trend_slope_lookback=self.config.strategy.trend_slope_lookback,
            breakout_lookback=self.config.strategy.breakout_lookback,
            adx_period=self.config.strategy.adx_period,
            adx_min=self.config.strategy.adx_min,
            use_trend_filter=self.config.strategy.use_trend_filter,
        )
    
    # ------------------------------------------------------------------
    def run(
        self,
        product_id: str,
        days: int = 365,
    ) -> BacktestResult:
        """Exécute un backtest."""
        log.info(f"Backtest: {product_id}, {days} jours")
        
        # Récupérer les données
        df = self._fetch_data(product_id, days)
        if len(df) == 0:
            raise ValueError(f"Aucune donnée récupérée pour {product_id}")
        
        # Initialisation
        cash = self.config.paper.starting_cash
        position: Optional[Position] = None
        dca_state = DCAState()
        
        equity_points: list[tuple[datetime, float]] = []
        trades: list[Trade] = []
        total_fees = 0.0
        bars_in_market = 0
        peak_equity = cash
        
        # Granularité en secondes
        gran_map = {
            "ONE_MINUTE": 60,
            "FIVE_MINUTE": 300,
            "FIFTEEN_MINUTE": 900,
            "THIRTY_MINUTE": 1800,
            "ONE_HOUR": 3600,
            "TWO_HOUR": 7200,
            "SIX_HOUR": 21600,
            "ONE_DAY": 86400,
        }
        gran_seconds = gran_map.get(self.config.market.granularity, 3600)
        
        # Attendre min_bars
        start_i = self.strategy.min_bars()
        
        for i in range(start_i, len(df)):
            row = df.iloc[i]
            timestamp = row.name
            close = float(row["close"])
            high = float(row["high"])
            low = float(row["low"])
            
            # Calculer equity
            equity = cash
            if position:
                equity += position.quantity * close
            
            equity_points.append((timestamp, equity))
            peak_equity = max(peak_equity, equity)
            
            if position:
                bars_in_market += 1
            
            # Évaluer le signal
            signal = self.strategy.evaluate(
                df.iloc[:i+1],
                in_position=position is not None,
                dca_state=dca_state,
                current_bar=i,
            )
            
            # Gestion de la position
            if position:
                # Mettre à jour le highest_high pour le trailing stop
                dca_state.highest_high = max(dca_state.highest_high, high)
                
                # PRIORITÉ AU DCA : si signal DCA, ne pas vérifier la sortie
                can_exit = True
                if signal.action == DCA_ENTER and dca_state.current_dca_level < self.config.strategy.dca_levels:
                    can_exit = False
                
                # Vérifier sortie (uniquement si ce n'est pas un signal DCA)
                if can_exit:
                    exit_signal = self._check_exit(
                        signal, position, close, low, dca_state, i
                    )
                else:
                    exit_signal = Signal(HOLD, close, "DCA en cours")
                
                if can_exit and exit_signal.action in (EXIT, TAKE_PROFIT):
                    # Sortie complète
                    exit_price = close
                    if exit_signal.action == EXIT:
                        exit_price = min(
                            dca_state.highest_high * (1 - self.config.strategy.trailing_stop_percentage / 100),
                            close
                        )
                    
                    # Calculer PnL
                    exit_fee = position.total_cost * self.fees_bps / 10000
                    proceeds = position.quantity * exit_price
                    pnl = proceeds - position.total_cost - position.entry_fees - exit_fee
                    
                    total_fees += position.entry_fees + exit_fee
                    
                    # Créer le trade
                    trade = Trade(
                        entry_time=position.entry_time,
                        exit_time=timestamp,
                        entry_price=position.avg_price,
                        exit_price=exit_price,
                        quantity=position.quantity,
                        entry_fee=position.entry_fees,
                        exit_fee=exit_fee,
                        pnl=pnl,
                        r_multiple=self._calculate_r_multiple(
                            position.avg_price, exit_price, position.entry_price
                        ),
                        reason=exit_signal.reason,
                        dca_level=position.dca_level,
                        is_dca=position.dca_level > 0,
                    )
                    trades.append(trade)
                    
                    # Mettre à jour le cash : cash précédent + proceeds + pnl
                    cash = cash + proceeds + pnl
                    
                    # Réinitialiser
                    position = None
                    dca_state.reset()
            
            # Entrée (initiale ou DCA)
            if signal.action in (ENTER_LONG, DCA_ENTER):
                if position is None:
                    # Nouvelle position
                    qty = self._calculate_position_size(
                        cash, close, signal.action == ENTER_LONG
                    )
                    if qty <= 0:
                        continue
                    
                    fee = qty * close * self.fees_bps / 10000
                    cost = qty * close + fee
                    
                    if cost > cash:
                        continue
                    
                    position = Position(
                        entry_time=timestamp,
                        entry_price=close,
                        quantity=qty,
                        total_cost=cost,
                        avg_price=close,
                        dca_level=0,
                        entry_fees=fee,
                    )
                    
                    cash -= cost
                    dca_state.on_enter(close, self.config.strategy.initial_stop_percentage, is_dca=False)
                    
                    # Enregistrer l'entrée initiale
                    self._record_dca_entry(trades, timestamp, close, qty, fee, 0, False)
                    
                elif signal.action == DCA_ENTER and dca_state.current_dca_level < self.config.strategy.dca_levels:
                    # Entrée DCA
                    if i - dca_state.last_dca_bar < self.config.strategy.dca_delay_bars:
                        continue
                    
                    # Calculer la quantité pour DCA (33% du capital initial)
                    dca_qty = self._calculate_dca_size(cash, close)
                    if dca_qty <= 0:
                        continue
                    
                    dca_fee = dca_qty * close * self.fees_bps / 10000
                    dca_cost = dca_qty * close + dca_fee
                    
                    if dca_cost > cash:
                        continue
                    
                    # Ajouter à la position
                    old_quantity = position.quantity
                    position.add_dca(close, dca_qty, dca_fee)
                    cash -= dca_cost
                    total_fees += dca_fee
                    
                    dca_state.on_enter(close, self.config.strategy.initial_stop_percentage, is_dca=True, dca_level=position.dca_level)
                    dca_state.last_dca_bar = i
                    
                    # Enregistrer l'entrée DCA
                    self._record_dca_entry(
                        trades, timestamp, close, dca_qty, dca_fee,
                        position.dca_level, True
                    )
        
        # Sortie forcée à la fin si position ouverte
        if position:
            exit_price = float(df.iloc[-1]["close"])
            pnl = position.quantity * exit_price - position.total_cost - position.entry_fees
            
            trade = Trade(
                entry_time=position.entry_time,
                exit_time=df.index[-1],
                entry_price=position.avg_price,
                exit_price=exit_price,
                quantity=position.quantity,
                entry_fee=position.entry_fees,
                exit_fee=0,
                pnl=pnl,
                r_multiple=self._calculate_r_multiple(
                    position.avg_price, exit_price, position.entry_price
                ),
                reason="Fin de backtest",
                dca_level=position.dca_level,
                is_dca=position.dca_level > 0,
            )
            trades.append(trade)
        
        # Calculer les stats
        equity_series = pd.Series(dict(equity_points))
        stats = self._calculate_stats(
            equity_series, trades, df, total_fees, bars_in_market,
            self.config.paper.starting_cash, gran_seconds
        )
        
        return BacktestResult(
            equity_curve=equity_series,
            trades=trades,
            stats=stats,
            price_data=df,
        )
    
    # ------------------------------------------------------------------
    def _fetch_data(self, product_id: str, days: int) -> pd.DataFrame:
        """Récupère les données de marché."""
        gran_map = {
            "ONE_MINUTE": 60,
            "FIVE_MINUTE": 300,
            "FIFTEEN_MINUTE": 900,
            "THIRTY_MINUTE": 1800,
            "ONE_HOUR": 3600,
            "TWO_HOUR": 7200,
            "SIX_HOUR": 21600,
            "ONE_DAY": 86400,
        }
        gran_seconds = gran_map.get(self.config.market.granularity, 3600)
        n_bars = int(days * 86400 / gran_seconds) + self.config.market.warmup_bars
        
        df = self.market_data.get_candles(
            product_id,
            self.config.market.granularity,
            gran_seconds,
            n_bars,
        )
        
        # Retirer la dernière bougie si incomplète
        if len(df) > 0:
            last_bar_time = df.index[-1].timestamp() + gran_seconds
            if last_bar_time > datetime.now(timezone.utc).timestamp():
                df = df.iloc[:-1]
        
        return df
    
    # ------------------------------------------------------------------
    def _check_exit(
        self,
        signal: Signal,
        position: Position,
        close: float,
        low: float,
        dca_state: DCAState,
        current_bar: int,
    ) -> Signal:
        """Vérifie si on doit sortir."""
        if signal.action in (EXIT, TAKE_PROFIT):
            return signal
        
        # Vérifier trailing stop
        trailing_stop = dca_state.highest_high * (1 - self.config.strategy.trailing_stop_percentage / 100)
        initial_stop = position.entry_price * (1 - self.config.strategy.initial_stop_percentage / 100)
        effective_stop = max(trailing_stop, initial_stop)
        
        if low <= effective_stop:
            return Signal(
                EXIT, close,
                f"STOP LOSS @ {effective_stop:.2f} (trailing: {trailing_stop:.2f}, initial: {initial_stop:.2f})"
            )
        
        # Vérifier take profit (UNIQUEMENT si activé)
        take_profit_r = self.config.strategy.take_profit_r_multiple
        if take_profit_r is not None:
            risk_per_unit = position.entry_price - effective_stop
            if risk_per_unit > 0:
                take_profit = position.entry_price + (take_profit_r * risk_per_unit)
                if close >= take_profit:
                    return Signal(
                        TAKE_PROFIT, close,
                        f"TAKE PROFIT @ {take_profit:.2f} (R={take_profit_r:.1f})"
                    )
        
        return Signal(HOLD, close, "Pas de sortie")
    
    # ------------------------------------------------------------------
    def _calculate_position_size(self, cash: float, price: float, is_initial: bool) -> float:
        """Calcule la taille de la position.
        
        Pour la stratégie DCA, on utilise dca_percentage du CAPITAL INITIAL
        pour TOUTES les entrées (initiale et DCA). Cela garantit que :
        - Entrée initiale : dca_percentage * capital_initial
        - DCA niveau 1 : dca_percentage * capital_initial
        - DCA niveau 2 : dca_percentage * capital_initial
        - Total : dca_levels * dca_percentage * capital_initial (<= 100%)
        
        On vérifie aussi que le cash disponible est suffisant.
        """
        if is_initial:
            # Pour la stratégie DCA, utiliser dca_percentage du capital initial
            dca_pct = self.config.strategy.dca_percentage
            initial_cash = self.config.paper.starting_cash
            position_amount = initial_cash * dca_pct
            
            qty = position_amount / price
            
            # Vérifier qu'on a assez de cash disponible
            max_qty = cash / price
            
            return min(qty, max_qty)
        
        return 0.0
    
    # ------------------------------------------------------------------
    def _calculate_dca_size(self, cash: float, price: float) -> float:
        """Calcule la taille pour une entrée DCA.
        
        Utilise le CAPITAL INITIAL pour chaque niveau DCA.
        Chaque niveau DCA utilise dca_percentage du capital initial,
        pas du cash disponible. Cela garantit que le total DCA ne dépasse
        pas 100% du capital initial.
        
        Exemple: avec dca_percentage=0.33 et starting_cash=10000$ :
        - DCA niveau 1: 10000 * 0.33 = 3300$ (si cash disponible >= 3300$)
        - DCA niveau 2: 10000 * 0.33 = 3300$ (si cash disponible >= 3300$)
        - DCA niveau 3: 10000 * 0.33 = 3300$ (si cash disponible >= 3300$)
        Total: 9900$ (99% du capital initial)
        """
        dca_pct = self.config.strategy.dca_percentage
        initial_cash = self.config.paper.starting_cash
        dca_amount = initial_cash * dca_pct
        
        qty = dca_amount / price
        
        # Vérifier qu'on a assez de cash disponible
        max_qty = cash / price
        
        return min(qty, max_qty)
    
    # ------------------------------------------------------------------
    def _calculate_r_multiple(self, entry_price: float, exit_price: float, initial_entry: float) -> float:
        """Calcule le R multiple."""
        risk_per_unit = entry_price - (entry_price * (1 - self.config.strategy.initial_stop_percentage / 100))
        if risk_per_unit <= 0:
            return 0.0
        
        profit_per_unit = exit_price - entry_price
        return profit_per_unit / risk_per_unit
    
    # ------------------------------------------------------------------
    def _record_dca_entry(
        self,
        trades: list[Trade],
        timestamp: datetime,
        price: float,
        qty: float,
        fee: float,
        dca_level: int,
        is_dca: bool,
    ) -> None:
        """Enregistre une entrée DCA (pour tracking)."""
        # On ne crée pas de trade, mais on enregistre l'information
        # pour le rapport final
        pass
    
    # ------------------------------------------------------------------
    def _calculate_stats(
        self,
        equity: pd.Series,
        trades: list[Trade],
        data: pd.DataFrame,
        total_fees: float,
        bars_in_market: int,
        start_equity: float,
        gran_seconds: int,
    ) -> dict:
        """Calcule toutes les statistiques."""
        end_equity = float(equity.iloc[-1]) if len(equity) > 0 else start_equity
        days = (data.index[-1] - data.index[0]).total_seconds() / 86400
        years = max(days / 365.25, 1e-9)
        
        # Performance
        total_return = end_equity / start_equity - 1
        cagr = (end_equity / start_equity) ** (1 / years) - 1 if end_equity > 0 else -1
        
        # Buy & Hold
        bh_return = float(data.iloc[-1]["close"] / data.iloc[0]["close"] - 1) if len(data) > 0 else 0
        
        # Drawdown
        roll_max = equity.cummax()
        max_dd = float(((equity - roll_max) / roll_max).min()) if len(equity) > 0 else 0.0
        
        # Sharpe
        rets = equity.pct_change().dropna()
        bars_per_year = 86400 * 365.25 / gran_seconds
        sharpe = float(rets.mean() / rets.std() * np.sqrt(bars_per_year)) if rets.std() > 0 else 0.0
        
        # Trades
        complete_trades = [t for t in trades if t.exit_time is not None]
        winning_trades = [t for t in complete_trades if t.pnl > 0]
        losing_trades = [t for t in complete_trades if t.pnl <= 0]
        
        n_trades = len(trades)
        n_complete = len(complete_trades)
        n_winning = len(winning_trades)
        n_losing = len(losing_trades)
        
        # DCA
        dca_trades = [t for t in trades if t.is_dca or t.dca_level > 0]
        total_dca_entries = sum(t.dca_level for t in trades)
        
        # Métriques trades
        gross_win = sum(t.pnl for t in winning_trades)
        gross_loss = -sum(t.pnl for t in losing_trades)
        
        stats = {
            "start": str(data.index[0].date()) if len(data) > 0 else "?",
            "end": str(data.index[-1].date()) if len(data) > 0 else "?",
            "days": days,
            "start_equity": start_equity,
            "end_equity": end_equity,
            "total_return_pct": total_return * 100,
            "cagr_pct": cagr * 100,
            "buy_hold_pct": bh_return * 100,
            "max_drawdown_pct": max_dd * 100,
            "sharpe": sharpe,
            "n_trades": n_trades,
            "n_complete_trades": n_complete,
            "n_dca_trades": len(dca_trades),
            "n_winning": n_winning,
            "n_losing": n_losing,
            "win_rate_pct": 100 * n_winning / n_complete if n_complete > 0 else 0.0,
            "avg_win": gross_win / n_winning if n_winning > 0 else 0.0,
            "avg_loss": -gross_loss / n_losing if n_losing > 0 else 0.0,
            "max_win": max([t.pnl for t in winning_trades]) if winning_trades else 0.0,
            "max_loss": min([t.pnl for t in losing_trades]) if losing_trades else 0.0,
            "avg_r": float(np.mean([t.r_multiple for t in complete_trades])) if complete_trades else 0.0,
            "profit_factor": gross_win / gross_loss if gross_loss > 0 else float("inf"),
            "total_fees": total_fees,
            "time_in_market_pct": 100 * bars_in_market / max(len(equity), 1),
            "total_dca_entries": total_dca_entries,
        }
        
        return stats


def run_backtest(
    config: BotConfig,
    days: int = 365,
    product_id: Optional[str] = None,
) -> BacktestResult:
    """Fonction utilitaire pour exécuter un backtest."""
    product = product_id or config.market.product_id
    backtester = DCABacktester(config)
    return backtester.run(product, days)
