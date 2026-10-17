#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from config import load_config
from backtest import run_backtest
import yaml
import tempfile
import os

# Config SANS DCA
config_dict = {
    'mode': 'paper',
    'market': {
        'product_id': 'BTC-USDC',
        'granularity': 'SIX_HOUR',
        'warmup_bars': 500
    },
    'strategy': {
        'entry_mode': 'dca_on_pullback',
        'dca_levels': 1,           # 1 seul niveau = PAS de DCA
        'dca_percentage': 0.33,
        'dca_delay_bars': 10000,   # Délai très long
        'dca_pullback_levels': [-100.0],  # Seuil impossible
        'initial_entry_condition': 'pullback',
        'breakout_lookback': 20,
        'use_trend_filter': False,  # Pas de filtre
        'trend_ema': 200,
        'trend_slope_lookback': 20,
        'adx_period': 14,
        'adx_min': 0
    },
    'risk': {
        'trailing_stop_percentage': 8.0,
        'initial_stop_percentage': 8.0,
        'take_profit_r_multiple': None,
        'risk_per_trade': 0.01,
        'max_position_pct': 0.33
    },
    'execution': {
        'prefer_maker': True,
        'limit_offset_bps': 5.0,
        'order_timeout_sec': 45,
        'stop_exit_is_market': True,
        'cooldown_bars': 0,
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
    print('=== BTC 365j (SANS DCA, trailing 8%) ===')
    print(f"Bot: {result.stats['total_return_pct']:+.2f}%")
    print(f"Buy & Hold: {result.stats['buy_hold_pct']:+.2f}%")
    print(f"Écart: {result.stats['total_return_pct'] - result.stats['buy_hold_pct']:+.2f}%")
    print(f"Max Drawdown: {result.stats['max_drawdown_pct']:.2f}%")
    print(f"Trades: {result.stats['n_trades']}")
    print(f"Capital final: ${result.stats['end_equity']:,.2f}")
finally:
    os.unlink(temp_config)
