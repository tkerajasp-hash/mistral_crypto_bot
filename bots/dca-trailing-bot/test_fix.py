#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from config import load_config
from backtest import run_backtest

# Test avec la config optimisée
config = load_config('config_optimized.yaml')

result = run_backtest(config, days=365, product_id='BTC-USDC')
print('=== BTC-USDC 365j (Config Optimisée) ===')
print(f"Bot: {result.stats['total_return_pct']:+.2f}%")
print(f"Buy & Hold: {result.stats['buy_hold_pct']:+.2f}%")
print(f"Écart: {result.stats['total_return_pct'] - result.stats['buy_hold_pct']:+.2f}%")
print(f"Max Drawdown: {result.stats['max_drawdown_pct']:.2f}%")
print(f"Trades: {result.stats['n_trades']}, DCA: {result.stats['total_dca_entries']}")
print(f"Capital final: ${result.stats['end_equity']:,.2f}")
