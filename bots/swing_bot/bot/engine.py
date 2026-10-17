"""Moteur : orchestre une decision par bougie cloturee, et la boucle d'execution."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import pandas as pd

from .broker import Broker, Fill
from .coinbase_client import MarketData, OrderNotFilled
from .config import VALID_GRANULARITIES, BotConfig
from . import exposure as expo
from .journal import BotState, Journal
from .notify import Notifier, disabled as _notifier_disabled, esc
from .risk import StopManager, position_size
from .strategy import ENTER_LONG, EXIT, HOLD, TrendStrategy

log = logging.getLogger("bot.engine")

MIN_NOTIONAL = 5.0  # on n'envoie pas d'ordre en dessous (poussiere)


class Bot:
    def __init__(
        self,
        cfg: BotConfig,
        market: MarketData,
        broker: Broker,
        strategy: TrendStrategy,
        journal: Journal,
        notifier: Notifier | None = None,
    ):
        self.cfg = cfg
        self.market = market
        self.broker = broker
        self.strategy = strategy
        self.journal = journal
        self.notifier = notifier or _notifier_disabled()
        self.state_path = cfg.logging.state_file

    # ==================================================================
    # Un "tick" = traiter la derniere bougie cloturee (idempotent)
    # ==================================================================
    def tick(self) -> None:
        cfg = self.cfg
        st = BotState.load(self.state_path)

        if st.halted:
            log.warning("Bot en arret (%s). Rien a faire.", st.halt_reason)
            return

        df = self._load_closed_candles()
        if len(df) < self.strategy.min_bars():
            log.warning("Pas assez d'historique (%d bougies).", len(df))
            return

        last_bar_time = df.index[-1].isoformat()
        if st.last_bar_time == last_bar_time:
            log.info("Bougie %s deja traitee.", last_bar_time)
            return

        bar = df.iloc[-1]
        mark = float(bar["close"])
        self.broker.mark_price(mark)

        st.bars_seen += 1
        st.last_bar_time = last_bar_time
        self._roll_day(st, mark)

        equity = self.broker.equity(mark)
        st.peak_equity = max(st.peak_equity, equity)

        # ---- Garde-fous globaux -------------------------------------
        if self._check_kill_switches(st, equity, mark):
            st.save(self.state_path)
            return

        htf_df = self._load_htf() if cfg.strategy.htf_filter else None
        sig = self.strategy.evaluate(df, in_position=st.in_position, htf_df=htf_df)
        log.info(
            "bar=%s close=%.2f pos=%s adx=%.1f -> %s (%s)",
            last_bar_time, mark, st.in_position, sig.adx, sig.action, sig.reason,
        )

        exp_row = None
        if cfg.risk.exposure_control:
            edata = expo.attach_market_signals(self.strategy.compute(df), cfg.risk)
            exp_row = edata.iloc[-1]

        prev_close = float(df.iloc[-2]["close"])

        just_exited = False
        if st.in_position:
            just_exited = self._manage_open_position(st, bar, sig, mark, exp_row, prev_close)

        if not st.in_position and not just_exited and not st.halted:
            self._maybe_enter(st, sig, mark, equity, exp_row)

        # ---- Journal equity ---------------------------------------
        pos = self.broker.get_position()
        self.journal.record_equity(
            bar_time=last_bar_time,
            equity=round(self.broker.equity(mark), 2),
            cash=round(self.broker.get_cash(), 2),
            position_qty=round(pos.qty, 10),
            mark=mark,
            in_position=st.in_position,
            stop=round(st.stop.get("stop", 0.0), 2) if st.in_position else "",
        )
        st.save(self.state_path)

    # ==================================================================
    # Boucle : dort jusqu'a (cloture de bougie + offset), tick, recommence
    # ==================================================================
    def run(self, once: bool = False) -> None:
        gran = self.cfg.market.granularity_seconds
        offset = self.cfg.execution.poll_offset_sec
        while True:
            try:
                self.tick()
            except Exception:  # noqa: BLE001
                log.exception("Erreur pendant le tick (on continue)")
            if once:
                return
            now = time.time()
            next_close = (int(now) // gran + 1) * gran + offset
            sleep_s = max(next_close - now, 5)
            log.info("Prochain tick dans %.0f s (%s)", sleep_s,
                     datetime.fromtimestamp(next_close, timezone.utc).isoformat())
            time.sleep(sleep_s)

    # ==================================================================
    # Helpers
    # ==================================================================
    def _load_closed_candles(self) -> pd.DataFrame:
        m = self.cfg.market
        df = self.market.get_candles(m.product_id, m.granularity, m.granularity_seconds, m.warmup_bars + 2)
        # retire la derniere bougie si elle est encore en cours
        now = time.time()
        bar_end = df.index[-1].timestamp() + m.granularity_seconds
        if bar_end > now:
            df = df.iloc[:-1]
        return df

    def _load_htf(self) -> pd.DataFrame | None:
        try:
            s = self.cfg.strategy
            secs = VALID_GRANULARITIES[s.htf_granularity]
            df = self.market.get_candles(self.cfg.market.product_id, s.htf_granularity, secs, s.htf_ema + 60)
            if df.index[-1].timestamp() + secs > time.time():
                df = df.iloc[:-1]
            return df
        except Exception:  # noqa: BLE001
            log.exception("Chargement HTF impossible")
            return None

    def _roll_day(self, st: BotState, equity_mark: float) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if st.day_key != today:
            st.day_key = today
            st.day_start_equity = self.broker.equity(equity_mark)
            if st.halt_reason == "daily_loss":       # la pause journaliere expire
                st.halted = False
                st.halt_reason = None
            if st.peak_equity <= 0:
                st.peak_equity = st.day_start_equity

    def _check_kill_switches(self, st: BotState, equity: float, mark: float) -> bool:
        r = self.cfg.risk
        if st.peak_equity > 0 and (st.peak_equity - equity) / st.peak_equity >= r.max_drawdown_pct:
            dd = (st.peak_equity - equity) / st.peak_equity
            self._flatten(st, mark, "kill switch: drawdown global")
            st.halted = True
            st.halt_reason = "max_drawdown"
            log.error("KILL SWITCH drawdown global -> arret complet.")
            self._notify_incident(
                "KILL SWITCH — DRAWDOWN GLOBAL",
                f"equity {equity:,.2f} ({dd:.1%} sous le pic {st.peak_equity:,.2f}). "
                f"Position soldee, trading ARRETE. Relance manuelle apres revue de state/.",
            )
            return True
        if st.day_start_equity > 0 and (st.day_start_equity - equity) / st.day_start_equity >= r.daily_max_loss_pct:
            dl = (st.day_start_equity - equity) / st.day_start_equity
            self._flatten(st, mark, "garde-fou: perte journaliere max")
            st.halted = True
            st.halt_reason = "daily_loss"
            log.error("Perte journaliere max atteinte -> pause jusqu'a demain.")
            self._notify_incident(
                "PAUSE JOURNALIERE",
                f"equity {equity:,.2f} ({dl:.1%} depuis l'ouverture du jour). "
                f"Position soldee, trading suspendu jusqu'a demain.",
            )
            return True
        return False

    # ---- gestion position ouverte --------------------------------
    def _manage_open_position(self, st: BotState, bar: pd.Series, sig, mark: float,
                              exp_row=None, prev_close: float | None = None) -> bool:
        sm = StopManager.from_dict(st.stop, self.cfg.risk)
        current_atr = sig.atr if sig.atr > 0 else sm.entry_atr
        sm.update(float(bar["high"]), float(bar["close"]), current_atr)
        st.stop = sm.to_dict()

        if sm.hit(float(bar["low"])):
            price = min(sm.stop, float(bar["close"]))  # on suppose une sortie au stop, borne par le close
            maker = not self.cfg.execution.stop_exit_is_market
            self._exit(st, price, maker=maker, reason=f"STOP LOSS @ {sm.stop:.2f}")
            return True

        bcs = self.cfg.risk.bar_crash_stop_pct
        if bcs > 0 and prev_close and (float(bar["close"]) / prev_close - 1.0) <= -bcs:
            bar_ret = float(bar["close"]) / prev_close - 1.0
            self._exit(st, mark, maker=False, reason=f"stop crash bougie ({bar_ret:+.1%})")
            return True

        if exp_row is not None and expo.crash_active(exp_row, self.cfg.risk):
            self._exit(st, mark, maker=self.cfg.execution.prefer_maker,
                       reason="frein de krach (chute brutale / vol)")
            return True

        if sig.action == EXIT:
            self._exit(st, mark, maker=self.cfg.execution.prefer_maker, reason=sig.reason)
            return True
        return False

    # ---- entree ------------------------------------------------
    def _maybe_enter(self, st: BotState, sig, mark: float, equity: float, exp_row=None) -> None:
        if st.bars_seen < st.cooldown_until_bar:
            log.info("Cooldown actif (encore %d bougies).", st.cooldown_until_bar - st.bars_seen)
            return
        if sig.action != ENTER_LONG:
            return
        if exp_row is not None and expo.crash_active(exp_row, self.cfg.risk):
            log.info("Frein de krach actif -> pas d'entree.")
            return

        ex, fees = self.cfg.execution, self.cfg.fees
        # cout aller-retour approximatif, en prix
        rt_bps = 2 * (fees.maker_bps if ex.prefer_maker else fees.taker_bps) + \
                 (0 if ex.prefer_maker else 2 * fees.slippage_bps)
        rt_cost = mark * rt_bps / 10_000
        if rt_cost > 0 and sig.atr < ex.min_edge_atr * rt_cost:
            log.info("Edge insuffisant: ATR %.2f < %.1f x cout %.2f", sig.atr, ex.min_edge_atr, rt_cost)
            return

        probe = StopManager(entry_price=mark, entry_atr=sig.atr, cfg=self.cfg.risk)
        qty = position_size(
            equity, mark, probe.stop,
            risk_per_trade=self.cfg.risk.risk_per_trade,
            max_position_pct=self.cfg.risk.max_position_pct,
            cash_available=self.broker.get_cash(),
        )
        if self.cfg.risk.exposure_control and exp_row is not None:
            est = expo.ExposureState(equity, st.peak_equity, st.bars_seen - st.last_exit_bar)
            mult, why = expo.entry_multiplier(exp_row, est, self.cfg.risk)
            if mult < 0.999:
                log.info("Exposition reduite (x%.2f): %s", mult, why)
            qty *= mult
        if qty * mark < MIN_NOTIONAL:
            log.info("Taille de position trop faible (%.2f), on passe.", qty * mark)
            return

        try:
            fill = self.broker.buy(qty, mark, maker=ex.prefer_maker)
        except OrderNotFilled:
            log.info("Ordre maker non rempli, nouvelle tentative a la prochaine bougie.")
            return
        if fill.qty <= 0:
            return

        sm = StopManager(entry_price=fill.price, entry_atr=sig.atr, cfg=self.cfg.risk)
        st.in_position = True
        st.entry_price = fill.price
        st.entry_time = datetime.now(timezone.utc).isoformat()
        st.qty = fill.qty
        st.initial_stop = sm.stop
        st.entry_fee = fill.fee
        st.stop = sm.to_dict()

        self.journal.record_trade(
            action="ENTRY", side="BUY", qty=round(fill.qty, 10), price=round(fill.price, 2),
            fee=round(fill.fee, 4), liquidity=fill.liquidity,
            equity=round(self.broker.equity(mark), 2), pnl="", r_multiple="",
            reason=sig.reason,
        )
        log.info("ENTREE %s %.8f @ %.2f (stop %.2f, risque %.2f)",
                 fill.liquidity, fill.qty, fill.price, sm.stop, fill.price - sm.stop)
        self._notify_entry(fill, sm.stop, sig.reason, self.broker.equity(mark))

    # ---- sortie ----------------------------------------------
    def _exit(self, st: BotState, ref_price: float, *, maker: bool, reason: str) -> None:
        qty = self.broker.get_position().qty
        if qty <= 0:
            st.in_position = False
            return
        try:
            fill = self.broker.sell(qty, ref_price, maker=maker)
        except OrderNotFilled:
            log.warning("Sortie maker non remplie -> bascule en market.")
            fill = self.broker.sell(qty, ref_price, maker=False)

        gross = (fill.price - st.entry_price) * fill.qty
        pnl = gross - st.entry_fee - fill.fee
        risk = max(st.entry_price - st.initial_stop, 1e-9)
        r_mult = (fill.price - st.entry_price) / risk

        self.journal.record_trade(
            action="EXIT", side="SELL", qty=round(fill.qty, 10), price=round(fill.price, 2),
            fee=round(fill.fee, 4), liquidity=fill.liquidity,
            equity=round(self.broker.equity(fill.price), 2),
            pnl=round(pnl, 2), r_multiple=round(r_mult, 2), reason=reason,
        )
        log.info("SORTIE %s %.8f @ %.2f | pnl=%.2f (%.2fR) | %s",
                 fill.liquidity, fill.qty, fill.price, pnl, r_mult, reason)
        self._notify_exit(fill, pnl, r_mult, reason, self.broker.equity(fill.price))

        st.in_position = False
        st.entry_price = 0.0
        st.qty = 0.0
        st.initial_stop = 0.0
        st.entry_fee = 0.0
        st.stop = {}
        st.cooldown_until_bar = st.bars_seen + self.cfg.execution.cooldown_bars
        st.last_exit_bar = st.bars_seen

    def _flatten(self, st: BotState, mark: float, reason: str) -> None:
        if st.in_position or self.broker.get_position().qty > 0:
            self._exit(st, mark, maker=False, reason=reason)

    # ==================================================================
    # Notifications (best-effort : jamais d'exception vers la boucle)
    # ==================================================================
    def _notify_entry(self, fill: Fill, stop: float, reason: str, equity: float) -> None:
        if not (self.notifier.enabled and self.cfg.notifications.on_trades):
            return
        try:
            pid = self.cfg.market.product_id
            quote = pid.split("-")[1]
            notional = fill.qty * fill.price
            self.notifier.send(
                f"\U0001F7E2 <b>ENTREE</b> {esc(pid)}\n"
                f"prix {fill.price:,.2f} · taille {fill.qty:.8f} (~{notional:,.0f} {esc(quote)})\n"
                f"stop {stop:,.2f} · risque {fill.price - stop:,.2f} {esc(quote)}/unite\n"
                f"motif : {esc(reason)}\n"
                f"equity {equity:,.2f} {esc(quote)}"
            )
        except Exception:  # noqa: BLE001
            log.exception("notif entree")

    def _notify_exit(self, fill: Fill, pnl: float, r_mult: float, reason: str, equity: float) -> None:
        if not (self.notifier.enabled and self.cfg.notifications.on_trades):
            return
        try:
            pid = self.cfg.market.product_id
            quote = pid.split("-")[1]
            icon = "\U0001F7E9" if pnl >= 0 else "\U0001F7E5"
            self.notifier.send(
                f"{icon} <b>SORTIE</b> {esc(pid)} · {r_mult:+.2f}R\n"
                f"prix {fill.price:,.2f} · PnL {pnl:+,.2f} {esc(quote)}\n"
                f"motif : {esc(reason)}\n"
                f"equity {equity:,.2f} {esc(quote)}"
            )
        except Exception:  # noqa: BLE001
            log.exception("notif sortie")

    def _notify_incident(self, title: str, detail: str) -> None:
        if not (self.notifier.enabled and self.cfg.notifications.on_incidents):
            return
        try:
            self.notifier.send(
                f"⚠️ <b>{esc(title)}</b> {esc(self.cfg.market.product_id)}\n{esc(detail)}"
            )
        except Exception:  # noqa: BLE001
            log.exception("notif incident")
