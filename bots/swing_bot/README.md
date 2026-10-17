# Bot de trading swing — Coinbase (BTC-USDC / ETH-USDC)

Bot **long-only** de suivi de tendance pour Coinbase Advanced Trade.
Trois objectifs, dans l'ordre :

1. **Ne pas se faire piéger** — un stop loss sérieux : stop initial ATR + plancher de perte dur + passage au point mort + stop suiveur « chandelier » qui ne redescend jamais.
2. **Profiter des vraies tendances haussières** — on n'entre que si la tendance de fond est haussière (EMA 200 croissante), confirmée par la force de tendance (ADX) et par l'unité de temps supérieure (daily). Entrée sur **cassure** (Donchian) ou, selon `entry_mode`, sur **rachat d'un repli** dans une tendance déjà haussière (preset `bull_rider_6h`).
3. **Minimiser les frais** — ordres **maker post-only** (souvent 0 frais sur BTC-USDC), **une seule décision par bougie clôturée**, cooldown après chaque sortie, filtre d'« edge » minimal avant d'entrer.

> ⚠️ **Rien ici n'est un conseil en investissement.** Le trading de cryptos peut faire perdre tout le capital. Commence en `paper`, lis le code, et n'active le mode `live` que si tu comprends chaque ligne. Tu es seul responsable des ordres passés.

---

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Test rapide (aucune clé requise, données publiques) :

```bash
python -m bot fetch --days 10
```

## Lancer un backtest

```bash
python -m bot backtest --days 365                 # stratégie active, paire de config.yaml
python -m bot backtest --strategy swing_1d --days 365
python -m bot -p ETH-USDC backtest --days 365      # même stratégie sur ETH-USDC
```

Sortie : performance, CAGR, comparaison buy & hold, max drawdown, Sharpe, nombre de trades, win rate, R moyen, coûts.
Les courbes détaillées sont écrites dans `data/backtest_equity_<PAIRE>.csv` et `data/backtest_trades_<PAIRE>.csv`.

### Validation « durcie » : `analyze`

Un seul chiffre de perf sur une seule fenêtre ne dit rien. `analyze` rejoue la stratégie sur
tout l'historique disponible (≈ 9 ans en 6h/1j) et sépare les **deux missions** du bot :

```bash
python -m bot analyze --strategy bull_rider_6h --days 3400
python -m bot analyze --strategy conservative_6h --days 3400 --folds 5 --dd-threshold 0.20
```

- **Phases de marché** : découpe l'historique en régimes haussier / baissier (bascule quand BTC
  recule de `--dd-threshold` sous son plus-haut) et compare, phase par phase, la stratégie au
  buy & hold → **% de la hausse captée** en marché haussier, **% de la baisse évitée** en marché baissier.
- **Walk-forward** : la même stratégie sur `--folds` sous-périodes successives → perf régulière
  ou portée par une seule fenêtre ?
- **Sensibilité** : fait varier `adx_min`, `breakout_lookback`, `initial_stop_atr`, `trailing_atr`
  de ±20-30 % → robuste, ou calé au petit bonheur (surapprentissage) ?
- Ajoute Sortino et MAR (CAGR / max drawdown).

## Choisir une stratégie : le dashboard

Plusieurs **presets** de stratégie sont définis dans [`strategies.yaml`](strategies.yaml)
(timeframe, mode d'entrée, seuil ADX, risque…). Pour les comparer :

```bash
python -m bot strategies                        # liste les presets
python -m bot dashboard --days 400               # backteste TOUS les presets -> dashboard_BTC-USDC.html
python -m bot -p ETH-USDC dashboard --days 400   # idem sur ETH-USDC -> dashboard_ETH-USDC.html
open dashboard_BTC-USDC.html
```

Le dashboard (fichier HTML autonome, aucune connexion) contient :

1. **État du marché** — les indicateurs actuels par unité de temps (prix vs EMA 200 et pente,
   ADX, ATR, niveaux de cassure/sortie Donchian, RSI, filtre daily) + le verdict « entrée possible / attente ».
2. **Tableau comparatif** — une ligne par stratégie : perf, CAGR, écart vs buy & hold, max drawdown,
   Sharpe, nb de trades, win rate, R moyen, profit factor, coûts, exposition, **signal actuel**.
   Tri par colonne, meilleure valeur de chaque colonne surlignée, détail des trades au clic.
3. **Courbes d'equity** et **courbes de drawdown** superposées.

Quand tu as choisi :

```bash
python -m bot select bull_rider_6h       # écrit `active:` dans strategies.yaml
python -m bot paper                       # le paper trading utilise cette stratégie
```

> Repères de lecture : privilégie un **max drawdown** faible et un **Sharpe** régulier, puis
> l'**écart vs buy & hold** (valeur ajoutée réelle) et le **R moyen** (espérance par trade).
> L'historique public Coinbase remonte plus loin en 6h/1j qu'en 1h : les fenêtres de test diffèrent
> (indiquées sur chaque ligne). Revalide sur une période haussière avant tout passage en live.

## Paper trading (simulation sur prix réels)

```bash
python -m bot paper            # boucle : un tick à chaque clôture de bougie
python -m bot paper --once     # un seul tick (pour cron)
python -m bot status           # état courant (position, stop, halted...)
```

**Stratégie recommandée (2026-10):** `bull_rider_optimized_6h`
- Bat le Buy & Hold sur BTC (+27.90% vs +23.98% sur 730 jours)
- Bat le Buy & Hold sur ETH (-5.42% vs -9.76% sur 730 jours)
- Max Drawdown: ~-14% sur BTC, ~-26% sur ETH

Pour l'activer:
```bash
python -m bot select bull_rider_optimized_6h
```

`paper` utilise la stratégie **active** de `strategies.yaml` (ou `--strategy <nom>` ponctuellement).
Le paper trading n'a **pas besoin de clés**. Le capital virtuel de départ est dans `config.yaml` (`paper.starting_cash`).
Journaux et état sont **suffixés par la paire** : `logs/trades_BTC-USDC.csv`, `logs/equity_BTC-USDC.csv`,
`state/bot_state_BTC-USDC.json`. Avec `-p ETH-USDC`, ce sont les fichiers `_ETH-USDC` — les deux paires
tournent donc en parallèle sans se gêner. `status` respecte aussi `-p`.

```bash
python -m bot paper                 # paire de config.yaml
python -m bot -p ETH-USDC paper      # ETH-USDC en parallèle (état/journaux séparés)
```

### En tâche de fond (cron)

Bougie 6 h → un tick toutes les 6 h. Adapter le chemin absolu à ta machine :

```cron
1 */6 * * * cd /Users/dev/Documents/crypto/python-swing-bot && .venv/bin/python -m bot paper --once >> logs/cron.log 2>&1
3 */6 * * * cd /Users/dev/Documents/crypto/python-swing-bot && .venv/bin/python -m bot -p ETH-USDC paper --once >> logs/cron.log 2>&1
```

(En granularité `ONE_HOUR`, mettre `1 * * * *` / `3 * * * *`.)

## Notifications Telegram

Alertes en direct pendant `paper` / `live` + un digest quotidien. Gratuit, sans dépendance lourde (juste `requests` ; `matplotlib` pour l'image du digest).

**Mise en place :**

1. Ouvre **@BotFather** sur Telegram → `/newbot` → récupère le **token**.
2. Écris un message à ton nouveau bot (sinon il ne peut pas t'écrire en premier).
3. Récupère ton **chat_id** : ouvre `https://api.telegram.org/bot<TON_TOKEN>/getUpdates` et lis `"chat":{"id": …}` (ou via @userinfobot).
4. Dans **`.env`** : `TELEGRAM_BOT_TOKEN=…` et `TELEGRAM_CHAT_ID=…`
5. Dans **`config.yaml`** : `notifications.enabled: true` (par défaut `false` ; `on_trades` / `on_incidents` pour affiner).

Si le token ou le chat_id manque, les notifications se désactivent silencieusement — le bot trade normalement. Un envoi qui échoue est loggé et **n'interrompt jamais** la boucle.

**Ce qui est envoyé :**

- **À chaque ENTRÉE / SORTIE** (pendant `paper` / `live`) : prix, taille, stop, motif, PnL et R sur les sorties, equity.
- **Incident** : pause journalière (`daily_max_loss_pct`) ou kill switch drawdown.
- **Digest** via `python -m bot report` : equity, perf depuis le départ, drawdown courant, position ouverte + PnL latent, trades clôturés (win rate, R cumulé, PnL réalisé), variation 24 h — **plus une image de la courbe d'equity** (départ, zone de drawdown, marqueurs entrées/sorties).

```bash
python -m bot report              # affiche + envoie (console + Telegram)
python -m bot report --no-send    # affiche seulement
python -m bot report --no-image   # texte seul sur Telegram
```

Digest quotidien à 8 h (cron) :

```cron
0 8 * * * cd /Users/dev/Documents/crypto/python-swing-bot && .venv/bin/python -m bot report >> logs/cron.log 2>&1
0 8 * * * cd /Users/dev/Documents/crypto/python-swing-bot && .venv/bin/python -m bot -p ETH-USDC report >> logs/cron.log 2>&1
```

## Brancher l'API Coinbase

1. **Crée une clé API** sur <https://portal.cdp.coinbase.com/> → onglet *API Keys* → *Create API key*.
   Permissions : **View + Trade**. **Ne coche pas « Transfer »** (aucun retrait possible avec cette clé). Restreins-la à ton IP si possible.
2. Renseigne les deux valeurs dans **`.env`** (déjà présent, ignoré par git) : `COINBASE_API_KEY` / `COINBASE_API_SECRET`.
3. **Vérifie la connexion (lecture seule, aucun ordre)** :

```bash
python -m bot account
```

→ affiche « Connexion Coinbase : OK », le prix spot, tes soldes USDC/BTC. Si la clé est absente / mal formée / sans permission, le message dit quoi corriger.

Tant que `config.yaml` reste `mode: paper`, **aucun ordre réel n'est envoyé** même avec des clés valides — `account` et `paper` te servent à tout valider d'abord.

## Passer en live (argent réel)

Une fois `python -m bot account` OK et la stratégie choisie (`bull_rider_aggressive_6h` par défaut) :

1. Dans `config.yaml` : `mode: live`.
2. Lance avec le garde-fou explicite (ajoute `-p ETH-USDC` avant `live` pour l'autre paire) :

```bash
python -m bot live --i-understand-live-trading --once
python -m bot -p ETH-USDC live --i-understand-live-trading --once
```

Le bot **refuse** de démarrer en live sans, à la fois : `mode: live`, le flag CLI `--i-understand-live-trading`, et des clés valides. Le premier ordre réel n'est passé que quand la stratégie génère une entrée sur une bougie clôturée.

---

## Comment la stratégie décide (résumé)

Évalué **uniquement sur bougies clôturées** :

| Étape | Condition | Rôle |
|---|---|---|
| Régime | selon `regime_mode` (voir ci-dessous) | ne trader que dans un marché haussier |
| Unité sup. | `daily close > EMA(htf_ema) daily` | éviter de contre-trader la grande tendance |
| Force | `ADX(14) ≥ adx_min` | écarter les marchés sans direction (range) |
| Entrée | selon `entry_mode` (voir ci-dessous) | capter la tendance |
| Edge | `ATR ≥ min_edge_atr × coût aller-retour` | ne pas trader pour rien quand les frais > 0 |

**`regime_mode`** :

| valeur | condition marché haussier |
|---|---|
| `strict` (défaut) | `close > EMA(trend_ema)` **et** pente `EMA(trend_ema)` > 0 sur `trend_slope_lookback` bougies — confirmé mais lent à valider un nouveau bull run |
| `fast` | `close > EMA(trend_ema)` **et** `EMA(ema_fast) > EMA(ema_slow)` — remplace la pente lente par un croisement d'EMA rapides, se retourne quelques jours après un creux (preset `bull_rider_aggressive_6h`) |

**`entry_mode`** (une fois régime + unité sup. + force validés) :

| valeur | déclencheur |
|---|---|
| `donchian_breakout` | cassure du plus haut des `breakout_lookback` clôtures (départ franc de tendance) |
| `ema_cross` | croisement `EMA(ema_fast)` au-dessus de `EMA(ema_slow)` |
| `pullback` | **achat du repli** : le prix est revenu `≤ EMA(ema_fast)` dans les `pullback_lookback` dernières bougies puis repasse au-dessus **en remontant** → entre plus tôt / plus souvent dans un bull run |
| `breakout_or_pullback` | l'un **ou** l'autre (cassure franche **+** rachats de repli) — utilisé par le preset `bull_rider_6h` |

**Sorties** (la première qui se déclenche) :
- stop loss touché (ATR / plancher dur / point mort / chandelier) ;
- cassure du plus bas des `exit_lookback` clôtures ;
- régime repassé baissier (`close < EMA(200)`).

Après chaque sortie : `cooldown_bars` bougies sans nouvelle entrée.

## Gestion du risque

- **Taille de position** calculée pour risquer `risk_per_trade` (0,75 % par défaut) de l'equity entre l'entrée et le stop initial, plafonnée par `max_position_pct` et le cash dispo.
- **Stop initial** = `max(entrée − initial_stop_atr × ATR, entrée × (1 − hard_max_loss_pct))`.
- **Point mort** dès +`breakeven_at_r` R de gain latent.
- **Stop suiveur** = `plus_haut_depuis_entrée − trailing_atr × ATR`, à cliquet (ne baisse jamais).
- **Stop « crash bougie »** (`bar_crash_stop_pct`, `0` = désactivé) : si une bougie clôture à `≤ −bar_crash_stop_pct` (ex. `0.05` = −5 % sur une 6h), sortie immédiate au marché. *Note : testé sur BTC, ça coûte du rendement sans réduire le drawdown (une bougie −5 % rebondit le plus souvent) — laissé désactivé par défaut.*
- **Kill switches** : `daily_max_loss_pct` (pause jusqu'au lendemain) et `max_drawdown_pct` (arrêt complet — relancer manuellement après avoir édité `state/bot_state.json`).

### Pilotage dynamique de l'exposition (optionnel)

Activé par `risk.exposure_control: true` (voir [`bot/exposure.py`](bot/exposure.py), preset `bull_rider_adaptive_6h`).
La taille de position est multipliée par un score d'état de risque qui ne fait que **réduire** :

1. **Vol targeting** — `× clip(vol_médiane / ATR%_courant, vol_mult_floor, vol_mult_cap)`. Un krach = un pic de volatilité → la taille tombe automatiquement.
2. **Frein de krach** — chute > `crash_return_atr × ATR%` sur `crash_return_bars` bougies, ou `close < EMA(ema_fast) − crash_ema_atr × ATR` → exposition **0** pendant `crash_brake_bars` bougies (sortie forcée si en position).
3. **Throttle de drawdown** — au-delà de `dd_throttle_start` sous le pic d'equity, taille réduite linéairement jusqu'à `dd_throttle_floor`.
4. **Anti-whipsaw** — taille `× whipsaw_mult` pendant `whipsaw_bars` bougies après chaque sortie.

Réf. : Moreira & Muir 2017, Harvey et al. 2018 (volatility targeting), Faber 2007, Perold & Sharpe 1988.

## Optimisation des frais

- `execution.prefer_maker: true` → entrées/sorties normales en **limit post-only** (fill maker, 0 frais sur BTC-USDC, pas de slippage).
- Les **sorties sur stop** passent en **market** (`stop_exit_is_market: true`) pour garantir l'exécution — la priorité est de couper la perte, pas d'économiser 1 bp.
- Si un ordre maker n'est pas rempli dans `order_timeout_sec`, il est **annulé** (pas de course au prix) et retenté à la bougie suivante.
- Le backtest applique `fees.assumed_roundtrip_bps` + `slippage_bps` même si tes frais réels sont à 0 : mieux vaut être pessimiste.

## Configuration

Tout est dans [`config.yaml`](config.yaml) (commenté). Les secrets restent dans `.env` (ignoré par git).
Paramètres clés : `market.product_id` (paire par défaut, surchargée par `-p`), `market.granularity`,
`strategy.adx_min`, `strategy.breakout_lookback`, `risk.risk_per_trade`, `risk.initial_stop_atr`,
`risk.trailing_atr`, `execution.cooldown_bars`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Structure

```
bot/
  config.py           chargement config + secrets + presets (strategies.yaml)
  indicators.py        EMA, ATR, ADX, RSI, Donchian (pandas pur)
  strategy.py          TrendStrategy : régime + cassure + ADX + sorties
  risk.py              position_size + StopManager (stop initial / trailing / point mort)
  broker.py            Broker (ABC) + PaperBroker (simulation frais/slippage)
  coinbase_client.py   MarketData (public, avec cache) + LiveBroker (SDK officiel)
  engine.py            Bot : une décision par bougie + boucle d'exécution
  journal.py           état JSON + journaux CSV
  backtest.py          backtest historique (frais inclus)
  analysis.py          validation durcie (régimes, walk-forward, sensibilité)
  exposure.py          pilotage dynamique de l'exposition (4 briques)
  dashboard.py         snapshot indicateurs + comparaison des presets -> dashboard.html
  notify.py            notifications Telegram (texte + image), best-effort
  report.py            digest equity/position/trades + graphe matplotlib
  __main__.py          CLI : fetch | account | strategies | dashboard | analyze | select | backtest | paper | live | status | report
config.yaml            réglages de base (dont notifications)
strategies.yaml        presets de stratégie + stratégie active
tests/                 pytest (indicateurs, risque, broker, stratégie, moteur, dashboard, exposure, notify, report)
```

## Limites connues / pistes

- Backtest : fills modélisés à la clôture de bougie (léger biais optimiste). Pas de reconstruction du carnet d'ordres.
- Le `LiveBroker` ne reconstitue pas le prix d'entrée moyen depuis l'exchange (utilisé seulement pour le calcul du PnL affiché) — l'état local fait foi.
- Un seul produit **par processus** (une position à la fois). BTC-USDC et ETH-USDC se lancent
  en parallèle via `-p`, mais chacun raisonne sur son propre capital `paper.starting_cash` : ce
  n'est pas une gestion de portefeuille commune (pas de risque agrégé entre les deux).
- L'historique de bougies publiques Coinbase remonte à ~1 an en 1 h.
