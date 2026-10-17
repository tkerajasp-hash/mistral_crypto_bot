#!/usr/bin/env python3
"""Test simple de paramètres pour ETH avec modification de strategies.yaml."""

# Au lieu de créer des configs dynamiquement, on va modifier strategies.yaml
# et lancer des backtests séquentiels

import subprocess
import time

# Stratégies à tester pour ETH
strategies_to_test = [
    # Nom, risk_per_trade, trailing_atr, initial_stop_atr, max_drawdown_pct
    ("eth_conservative", 0.02, 4.0, 3.0, 0.15),
    ("eth_modern", 0.025, 3.5, 3.0, 0.15),
    ("eth_balanced", 0.025, 4.0, 3.0, 0.20),
    ("eth_optimized", 0.03, 3.5, 3.5, 0.20),
]

# Template pour strategies.yaml
STRATEGY_TEMPLATE = """
  # ===========================================================================
  # {name} -- Stratégie optimisée pour ETH
  # risk_per_trade: {risk}%, trailing_atr: {trail}, initial_stop_atr: {init_stop}
  # ===========================================================================
  {name}:
    market: {{granularity: SIX_HOUR}}
    strategy:
      entry_mode: breakout_or_pullback
      regime_mode: fast
      trend_ema: 150
      breakout_lookback: 30
      exit_lookback: 20
      ema_fast: 20
      ema_slow: 50
      pullback_lookback: 6
      adx_min: 18
      htf_filter: true
      htf_granularity: ONE_DAY
    risk:
      risk_per_trade: {risk}
      max_position_pct: 0.95
      initial_stop_atr: {init_stop}
      trailing_atr: {trail}
      hard_max_loss_pct: 0.08
      daily_max_loss_pct: 0.05
      max_drawdown_pct: {max_dd}
"""

print("Testing different parameter combinations for ETH-USDC...")
print("=" * 80)

results = []

for name, risk, trail, init_stop, max_dd in strategies_to_test:
    # Ajouter la stratégie à strategies.yaml
    with open('strategies.yaml', 'a') as f:
        f.write(STRATEGY_TEMPLATE.format(
            name=name,
            risk=risk,
            trail=trail,
            init_stop=init_stop,
            max_dd=max_dd
        ))
    
    # Lancer le backtest
    start = time.time()
    try:
        result = subprocess.run(
            ['.venv/bin/python', '-m', 'bot', '-p', 'ETH-USDC', 'backtest', '--strategy', name, '--days', '730'],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # Extraire les stats du output
        output = result.stdout
        if 'Performance' in output and 'Buy & Hold' in output:
            # Parser les stats
            lines = output.split('\n')
            stats = {}
            for line in lines:
                if 'Performance:' in line:
                    stats['perf'] = float(line.split(':')[-1].strip().replace('%', '').replace('+', ''))
                if 'Buy & Hold:' in line:
                    stats['bh'] = float(line.split(':')[-1].strip().replace('%', '').replace('+', ''))
                if 'Max drawdown:' in line:
                    stats['mdd'] = float(line.split(':')[-1].strip().replace('%', ''))
                if 'Trades:' in line:
                    stats['trades'] = int(line.split(':')[-1].strip().split()[0])
                if 'win rate' in line or 'Win' in line:
                    # Extraire win rate
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if '%' in p:
                            stats['wr'] = float(p.replace('%', ''))
                            break
            
            if 'perf' in stats and 'bh' in stats:
                excess = stats['perf'] - stats['bh']
                results.append({
                    'name': name,
                    'risk': risk,
                    'trail': trail,
                    'init_stop': init_stop,
                    'max_dd': max_dd,
                    'perf': stats['perf'],
                    'bh': stats['bh'],
                    'excess': excess,
                    'mdd': stats['mdd'],
                    'trades': stats.get('trades', 0),
                    'wr': stats.get('wr', 0)
                })
                
                elapsed = time.time() - start
                print(f"{name}: risk={risk*100:.0f}% trail={trail} init={init_stop} max_dd={max_dd}")
                print(f"  Perf={stats['perf']:+.2f}% BH={stats['bh']:+.2f}% Excess={excess:+.2f}% MDD={stats['mdd']:.2f}% "
                      f"Trades={stats.get('trades', '?')} WR={stats.get('wr', '?'):.1f}% ({elapsed:.1f}s)")
    except Exception as e:
        print(f"Erreur avec {name}: {e}")

# Nettoyer strategies.yaml (retirer les stratégies test)
print("\nNettoyage des stratégies test...")
with open('strategies.yaml', 'r') as f:
    content = f.read()

# Retirer les stratégies eth_*
for name, _, _, _, _ in strategies_to_test:
    content = content.replace(f'  {name}:\n', '')
    # Retirer tout le bloc
    lines = content.split('\n')
    new_lines = []
    skip = False
    for line in lines:
        if f'  {name}:' in line:
            skip = True
        if skip:
            if line.strip() and not line.startswith(' '):
                skip = False
            else:
                continue
        new_lines.append(line)
    content = '\n'.join(new_lines)

with open('strategies.yaml', 'w') as f:
    f.write(content)

# Afficher les meilleurs résultats
print("\n" + "="*80)
print("MEILLEURS RÉSULTATS SUR ETH:")
print("="*80)

if results:
    # Filtrer ceux qui battent le BH
    best = [r for r in results if r['excess'] > 0]
    best.sort(key=lambda x: x['excess'], reverse=True)
    
    if best:
        print("Stratégies qui battent le Buy & Hold:")
        for r in best:
            print(f"{r['name']}: Excess={r['excess']:+.2f}% MDD={r['mdd']:.2f}% "
                  f"Perf={r['perf']:+.2f}% BH={r['bh']:+.2f}%")
    else:
        print("Aucune stratégie ne bat le Buy & Hold")
    
    print("\nToutes les stratégies:")
    for r in results:
        print(f"{r['name']}: Excess={r['excess']:+.2f}% MDD={r['mdd']:.2f}% "
              f"Perf={r['perf']:+.2f}% BH={r['bh']:+.2f}%")
else:
    print("Aucun résultat valide")
