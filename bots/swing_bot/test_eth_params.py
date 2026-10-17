#!/usr/bin/env python3
"""Test de différentes combinaisons de paramètres pour ETH-USDC."""

from bot.backtest import run_backtest
from bot.config import load_config

# Paramètres de base pour ETH
BASE_CONFIG = {
    'market': {'product_id': 'ETH-USDC', 'granularity': 'SIX_HOUR', 'warmup_bars': 400},
    'strategy': {
        'entry_mode': 'breakout_or_pullback',
        'regime_mode': 'fast',
        'trend_ema': 150,
        'breakout_lookback': 30,
        'exit_lookback': 20,
        'ema_fast': 20,
        'ema_slow': 50,
        'pullback_lookback': 6,
        'adx_min': 18,
        'htf_filter': True,
        'htf_granularity': 'ONE_DAY',
        'htf_ema': 50
    },
    'risk': {
        'atr_period': 14,
        'breakeven_at_r': 1.0,
        'breakeven_offset_atr': 0.25,
        'hard_max_loss_pct': 0.08,
        'daily_max_loss_pct': 0.05,
    },
    'fees': {'maker_bps': 0.0, 'taker_bps': 0.0, 'assumed_roundtrip_bps': 10.0, 'slippage_bps': 2.0},
    'execution': {'prefer_maker': True, 'limit_offset_bps': 5.0, 'order_timeout_sec': 45, 'stop_exit_is_market': True, 'cooldown_bars': 3, 'min_edge_atr': 1.0, 'poll_offset_sec': 20},
    'paper': {'starting_cash': 10000.0},
    'mode': 'paper',
    'logging': {'level': 'INFO', 'state_file': 'state/bot_state.json', 'trades_csv': 'logs/trades.csv', 'equity_csv': 'logs/equity.csv'}
}

# Combinaisons à tester
PARAMS_LIST = [
    # risk_per_trade, trailing_atr, initial_stop_atr, max_drawdown_pct
    (0.025, 4.0, 3.0, 0.20),
    (0.03, 4.0, 3.0, 0.20),
    (0.025, 3.5, 3.0, 0.20),
    (0.03, 3.5, 3.0, 0.20),
    (0.025, 4.0, 3.5, 0.20),
    (0.03, 4.0, 3.5, 0.20),
    (0.02, 4.0, 3.0, 0.15),
    (0.025, 4.5, 3.5, 0.20),
    (0.02, 3.5, 3.0, 0.15),
    (0.025, 3.0, 3.0, 0.15),
    (0.03, 5.0, 3.0, 0.20),
    (0.02, 4.0, 4.0, 0.15),
]

import time

print("Testing different parameter combinations for ETH-USDC...")
print("=" * 80)

results = []

for risk_trade, trail_atr, init_stop, max_dd in PARAMS_LIST:
    cfg_dict = BASE_CONFIG.copy()
    cfg_dict['risk'] = {
        'risk_per_trade': risk_trade,
        'max_position_pct': 0.95,
        'atr_period': 14,
        'initial_stop_atr': init_stop,
        'trailing_atr': trail_atr,
        'breakeven_at_r': 1.0,
        'breakeven_offset_atr': 0.25,
        'hard_max_loss_pct': 0.08,
        'daily_max_loss_pct': 0.05,
        'max_drawdown_pct': max_dd
    }
    
    try:
        start = time.time()
        result = run_backtest(load_config(), days=730, save_dir=None)
        # Note: load_config() loads from file, not from dict
        # We need to create a BotConfig from dict
        from bot.config import BotConfig, StrategyConfig, RiskConfig, MarketConfig, ExecutionConfig, FeesConfig, PaperConfig, LoggingConfig
        
        cfg = BotConfig(
            mode='paper',
            market=MarketConfig(
                product_id='ETH-USDC',
                granularity='SIX_HOUR',
                warmup_bars=400
            ),
            strategy=StrategyConfig(
                entry_mode='breakout_or_pullback',
                regime_mode='fast',
                trend_ema=150,
                breakout_lookback=30,
                exit_lookback=20,
                ema_fast=20,
                ema_slow=50,
                pullback_lookback=6,
                adx_min=18,
                adx_period=14,
                htf_filter=True,
                htf_granularity='ONE_DAY',
                htf_ema=50
            ),
            risk=RiskConfig(
                risk_per_trade=risk_trade,
                max_position_pct=0.95,
                atr_period=14,
                initial_stop_atr=init_stop,
                trailing_atr=trail_atr,
                breakeven_at_r=1.0,
                breakeven_offset_atr=0.25,
                hard_max_loss_pct=0.08,
                daily_max_loss_pct=0.05,
                max_drawdown_pct=max_dd
            ),
            fees=FeesConfig(
                maker_bps=0.0,
                taker_bps=0.0,
                assumed_roundtrip_bps=10.0,
                slippage_bps=2.0
            ),
            execution=ExecutionConfig(
                prefer_maker=True,
                limit_offset_bps=5.0,
                order_timeout_sec=45,
                stop_exit_is_market=True,
                cooldown_bars=3,
                min_edge_atr=1.0,
                poll_offset_sec=20
            ),
            paper=PaperConfig(starting_cash=10000.0),
            logging=LoggingConfig(
                level='INFO',
                state_file='state/bot_state_ETH-USDC.json',
                trades_csv='logs/trades_ETH-USDC.csv',
                equity_csv='logs/equity_ETH-USDC.csv'
            )
        )
        
        result = run_backtest(cfg, days=730, save_dir=None)
        stats = result.stats
        excess = stats['total_return_pct'] - stats['buy_hold_pct']
        
        elapsed = time.time() - start
        
        results.append({
            'risk_per_trade': risk_trade,
            'trailing_atr': trail_atr,
            'initial_stop_atr': init_stop,
            'max_drawdown_pct': max_dd,
            'perf': stats['total_return_pct'],
            'bh': stats['buy_hold_pct'],
            'excess': excess,
            'mdd': stats['max_drawdown_pct'],
            'trades': stats['n_trades'],
            'win_rate': stats['win_rate_pct']
        })
        
        print(f"risk={risk_trade*100:.0f}% trail={trail_atr} init={init_stop} max_dd={max_dd}: "
              f"Perf={stats['total_return_pct']:+.2f}% BH={stats['buy_hold_pct']:+.2f}% "
              f"Excess={excess:+.2f}% MDD={stats['max_drawdown_pct']:.2f}% "
              f"Trades={stats['n_trades']} WR={stats['win_rate_pct']:.1f}% ({elapsed:.1f}s)")
        
    except Exception as e:
        import traceback
        print(f"Erreur avec risk={risk_trade} trail={trail_atr}: {e}")
        traceback.print_exc()

# Afficher les meilleurs résultats
print("\n" + "="*80)
print("MEILLEURS RÉSULTATS SUR ETH (Excess > 0 et MDD > -20%):")
print("="*80)
best = [r for r in results if r['excess'] > 0 and r['mdd'] > -20]
best.sort(key=lambda x: x['excess'], reverse=True)

if best:
    for r in best[:5]:
        print(f"risk={r['risk_per_trade']*100:.0f}% trail={r['trailing_atr']} init={r['initial_stop_atr']}: "
              f"Perf={r['perf']:+.2f}% Excess={r['excess']:+.2f}% MDD={r['mdd']:.2f}% "
              f"Trades={r['trades']} WR={r['win_rate']:.1f}%")
else:
    print("Aucune combinaison ne bat le BH avec MDD < -20%")
    print("\nAfficher toutes les combinaisons avec excess > 0:")
    all_positive = [r for r in results if r['excess'] > 0]
    all_positive.sort(key=lambda x: x['excess'], reverse=True)
    for r in all_positive:
        print(f"risk={r['risk_per_trade']*100:.0f}% trail={r['trailing_atr']} init={r['initial_stop_atr']}: "
              f"Perf={r['perf']:+.2f}% Excess={r['excess']:+.2f}% MDD={r['mdd']:.2f}%")
