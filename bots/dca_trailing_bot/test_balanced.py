#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from config import load_config
from backtest import run_backtest
import yaml
import tempfile
import os

# Config ÉQUILIBRÉE : bat B&H avec drawdown raisonnable
config_dict = {
    'mode': 'paper',
    'market': {
        'product_id': 'BTC-USDC',
        'granularity': 'SIX_HOUR',
        'warmup_bars': 500
    },
    'strategy': {
        'entry_mode': 'dca_on_pullback',
        'dca_levels': 2,           # 2 niveaux (au lieu de 3)
        'dca_percentage': 0.33,
        'dca_delay_bars': 3,      # 3 bougies entre DCA
        'dca_pullback_levels': [-3.0, -6.0],
        'initial_entry_condition': 'pullback',
        'breakout_lookback': 20,
        'use_trend_filter': False,  # Pas de filtre pour trader plus
        'trend_ema': 50,
        'trend_slope_lookback': 10,
        'adx_period': 14,
        'adx_min': 0
    },
    'risk': {
        'trailing_stop_percentage': 10.0,  # 10% (plus serré)
        'initial_stop_percentage': 10.0,
        'take_profit_r_multiple': None,
        'risk_per_trade': 0.01,
        'max_position_pct': 0.66
    },
    'execution': {
        'prefer_maker': True,
        'limit_offset_bps': 5.0,
        'order_timeout_sec': 45,
        'stop_exit_is_market': True,
        'cooldown_bars': 6,      # 6 bougies SIX_HOUR = 1.5 jours
        'poll_offset_sec': 20
    },
    'paper': {'starting_cash': 10000.0},
    'notifications': {'enabled': False},
    'discord': {'enabled': False},
    'logging': {'level': 'INFO'}
}

with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
    yaml.dump(config_dict, f)
    temp_config = f.name

try:
    config = load_config(temp_config)
    result = run_backtest(config, days=365, product_id='BTC-USDC')
    print('=== BTC 365j (Équilibré) ===')
    print(f"Bot: {result.stats['total_return_pct']:+.2f}%")
    print(f"Buy & Hold: {result.stats['buy_hold_pct']:+.2f}%")
    print(f"Écart: {result.stats['total_return_pct'] - result.stats['buy_hold_pct']:+.2f}%")
    print(f"Max Drawdown: {result.stats['max_drawdown_pct']:.2f}%")
    print(f"Trades: {result.stats['n_trades']}, DCA: {result.stats['total_dca_entries']}")
    print(f"Capital final: ${result.stats['end_equity']:,.2f}")
finally:
    os.unlink(temp_config)
