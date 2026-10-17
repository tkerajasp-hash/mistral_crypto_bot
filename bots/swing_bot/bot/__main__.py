"""Point d'entree CLI.

    python -m bot fetch      [--days 90]                  # verifie l'acces aux donnees (public)
    python -m bot account                                 # verifie la connexion API Coinbase (lecture seule)
    python -m bot strategies                              # liste les presets (strategies.yaml)
    python -m bot dashboard  [--days 400]                 # backteste TOUS les presets -> dashboard_<PRODUIT>.html
    python -m bot analyze    [--days 3400] [--strategy X] # validation durcie (regimes + walk-forward + sensibilite)
    python -m bot select <nom>                            # definit la strategie active
    python -m bot backtest   [--days 365] [--strategy X]  # teste une strategie sur historique
    python -m bot paper      [--once] [--strategy X]      # trading simule sur prix reels
    python -m bot live       --i-understand-live-trading  # vrais ordres (cles requises)
    python -m bot status                                  # etat courant du bot
    python -m bot report     [--no-send] [--no-image]     # digest -> console + Telegram (cron 1x/j)

Option globale (avant la sous-commande) : -p / --product BTC-USDC | ETH-USDC | ...
Chaque produit a ses propres fichiers d'etat / journaux / sorties (suffixe _<PRODUIT>).
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

from .backtest import run_backtest
from .broker import PaperBroker
from .config import list_strategies, load_config
from .engine import Bot
from .journal import BotState, Journal
from .logging_setup import setup_logging
from .strategy import TrendStrategy

log = logging.getLogger("bot")


def _build_paper_bot(cfg):
    from .coinbase_client import MarketData
    from .notify import from_config as _notifier

    market = MarketData()
    broker = PaperBroker(cfg)
    journal = Journal(cfg.logging.trades_csv, cfg.logging.equity_csv)
    return Bot(cfg, market, broker, TrendStrategy(cfg.strategy), journal, _notifier(cfg))


def _build_live_bot(cfg):
    from .coinbase_client import LiveBroker, MarketData
    from .notify import from_config as _notifier

    market = MarketData()
    broker = LiveBroker(cfg, market)
    journal = Journal(cfg.logging.trades_csv, cfg.logging.equity_csv)
    return Bot(cfg, market, broker, TrendStrategy(cfg.strategy), journal, _notifier(cfg))


def cmd_fetch(cfg, args):
    from .coinbase_client import MarketData

    m = cfg.market
    md = MarketData()
    n = int(args.days * 86400 / m.granularity_seconds)
    df = md.get_candles(m.product_id, m.granularity, m.granularity_seconds, n)
    print(f"{len(df)} bougies {m.granularity} pour {m.product_id}")
    print(f"de {df.index[0]}  a  {df.index[-1]}")
    print(df.tail(5).to_string())
    print(f"prix spot actuel : {md.spot_price(m.product_id):,.2f}")


def cmd_backtest(cfg, args):
    if cfg.active_strategy:
        print(f"strategie : {cfg.active_strategy}\n")
    res = run_backtest(cfg, days=args.days)
    print(res.summary())


def cmd_account(cfg, args):
    """Verifie la connexion a l'API Coinbase (lecture seule) : cle valide, permissions, soldes."""
    from .coinbase_client import LiveBroker, MarketData

    if not cfg.secrets.present:
        sys.exit(
            "Aucune cle API chargee.\n"
            "  1. cp .env.example .env\n"
            "  2. renseigne COINBASE_API_KEY / COINBASE_API_SECRET (cle creee sur "
            "https://portal.cdp.coinbase.com/ , permissions View + Trade)\n"
            "  3. relance : python -m bot account"
        )

    md = MarketData()
    pid = cfg.market.product_id
    try:
        broker = LiveBroker(cfg, md)
    except Exception as exc:  # noqa: BLE001
        sys.exit(
            f"Connexion Coinbase impossible : {exc}\n"
            "Verifie : cle active, secret complet (avec les \\n), et permission 'View' accordee."
        )

    try:
        bals = broker.balances()
        spot = md.spot_price(pid)
    except Exception as exc:  # noqa: BLE001
        sys.exit(f"Cle chargee mais l'appel a echoue : {exc}\n(permission 'View' manquante ?)")

    base, quote = pid.split("-")
    base_bal = bals.get(base, 0.0)
    quote_bal = bals.get(quote, 0.0)
    print("Connexion Coinbase : OK  (cle API valide, lecture)")
    print(f"  Produit        : {pid}   spot {spot:,.2f}")
    print(f"  Solde {quote:<8}: {quote_bal:,.2f}")
    print(f"  Solde {base:<8}: {base_bal:,.8f}   (~{base_bal * spot:,.2f} {quote})")
    print(f"  Increments     : base {broker.base_increment}  quote {broker.quote_increment}")
    print(f"\n  mode (config.yaml) : {cfg.mode}")
    if cfg.mode != "live":
        print("  -> encore en simulation. Pour trader en reel : mode: live dans config.yaml")
        print("     puis  python -m bot live --i-understand-live-trading --once")
    print("\n  Le test de trade reel se fait uniquement via la commande 'live' "
          "(jamais automatiquement).")


def cmd_analyze(cfg, args):
    from .analysis import format_report

    if cfg.active_strategy:
        print(f"strategie : {cfg.active_strategy}\n")
    print(format_report(cfg, days=args.days, dd_threshold=args.dd_threshold, folds=args.folds))


def cmd_strategies(cfg, args):
    active, presets = list_strategies()
    if not presets:
        print("Aucun preset dans strategies.yaml")
        return
    print(f"{'ACTIF':<6} {'NOM':<18} GRANULARITE  ENTREE             ADX  RISK/TRADE")
    for name, spec in presets.items():
        s = spec.get("strategy", {})
        r = spec.get("risk", {})
        mark = "  ->" if name == active else ""
        print(f"{mark:<6} {name:<18} {spec.get('market', {}).get('granularity', '?'):<11}  "
              f"{s.get('entry_mode', 'donchian_breakout'):<18} {str(s.get('adx_min', '-')):<4} "
              f"{r.get('risk_per_trade', '(defaut)')}")
    print(f"\nactive: {active}")


def _write_active(name: str, path: str = "strategies.yaml") -> None:
    p = Path(path)
    text = p.read_text()
    if re.search(r"(?m)^active:\s*.*$", text):
        text = re.sub(r"(?m)^active:\s*.*$", f"active: {name}", text, count=1)
    else:
        text = f"active: {name}\n" + text
    p.write_text(text)


def cmd_select(cfg, args):
    _, presets = list_strategies()
    if args.name not in presets:
        sys.exit(f"strategie inconnue: {args.name}. Disponibles: {', '.join(presets)}")
    _write_active(args.name)
    print(f"Strategie active -> {args.name}")
    print("Verifie avec : python -m bot strategies   |   lance : python -m bot paper")


def cmd_dashboard(cfg, args):
    from .dashboard import build_dashboard

    out = build_dashboard(days=args.days, out=args.out, product=args.product)
    print(f"\nDashboard genere : {out}")
    print(f"Ouvre-le dans un navigateur : open {out}")


def cmd_paper(cfg, args):
    cfg.mode = "paper"
    bot = _build_paper_bot(cfg)
    log.info("=== PAPER TRADING === %s %s | capital virtuel %.2f",
             cfg.market.product_id, cfg.market.granularity, cfg.paper.starting_cash)
    bot.run(once=args.once)


def cmd_live(cfg, args):
    if not args.i_understand_live_trading:
        sys.exit("Refus: ajoute --i-understand-live-trading pour trader en reel.")
    if cfg.mode != "live":
        sys.exit("Refus: mets 'mode: live' dans config.yaml.")
    if not cfg.secrets.present:
        sys.exit("Refus: cles COINBASE_API_KEY / COINBASE_API_SECRET absentes de .env.")
    bot = _build_live_bot(cfg)
    log.warning("=== LIVE TRADING (ARGENT REEL) === %s %s", cfg.market.product_id, cfg.market.granularity)
    bot.run(once=args.once)


def cmd_report(cfg, args):
    """Digest (equity, position, trades, drawdown) : affiche, et envoie sur Telegram si active."""
    from .notify import from_config as _notifier
    from .report import build_digest, equity_chart

    digest = build_digest(cfg)
    # version console : on retire les balises HTML de Telegram
    print(re.sub(r"</?[^>]+>", "", digest))

    if args.no_send:
        return
    notif = _notifier(cfg)
    if not notif.enabled:
        print("\n(notifications desactivees : notifications.enabled + TELEGRAM_* dans .env)")
        return
    notif.send(digest)
    if not args.no_image:
        img = equity_chart(cfg)
        if img:
            notif.send_photo(img, caption=f"Equity — {cfg.market.product_id}")
            print(f"\nEnvoye sur Telegram (+ image {img}).")
        else:
            print("\nEnvoye sur Telegram (image indisponible).")
    else:
        print("\nEnvoye sur Telegram.")


def cmd_status(cfg, args):
    st = BotState.load(cfg.logging.state_file)
    print(f"mode config        : {cfg.mode}")
    print(f"paire              : {cfg.market.product_id} ({cfg.market.granularity})")
    print(f"en position        : {st.in_position}")
    if st.in_position:
        print(f"  entree           : {st.entry_price:.2f}  x {st.qty:.8f}")
        print(f"  stop courant     : {st.stop.get('stop', 0):.2f}")
        print(f"  stop initial     : {st.initial_stop:.2f}")
    print(f"bougies vues       : {st.bars_seen}")
    print(f"cooldown jusqu'a   : bougie {st.cooldown_until_bar}")
    print(f"equity pic         : {st.peak_equity:.2f}")
    print(f"halted             : {st.halted}  ({st.halt_reason})")


def main(argv=None):
    p = argparse.ArgumentParser(prog="bot", description="Bot de trading swing Coinbase")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("-p", "--product", default=None,
                   help="paire a trader (ex. BTC-USDC, ETH-USDC). Defaut: market.product_id de config.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)

    def with_strategy(parser):
        parser.add_argument("--strategy", default=None,
                            help="preset de strategies.yaml (sinon: la strategie 'active')")
        return parser

    sp = sub.add_parser("fetch", help="verifie l'acces aux donnees de marche (public)")
    sp.add_argument("--days", type=int, default=30)
    with_strategy(sp)
    sp.set_defaults(func=cmd_fetch)

    sp = sub.add_parser("account", help="verifie la connexion API Coinbase (cle, permissions, soldes) -- lecture seule")
    sp.set_defaults(func=cmd_account)

    sp = sub.add_parser("strategies", help="liste les presets de strategies")
    sp.set_defaults(func=cmd_strategies)

    sp = sub.add_parser("dashboard", help="backteste tous les presets -> dashboard_<PRODUIT>.html")
    sp.add_argument("--days", type=int, default=400)
    sp.add_argument("--out", default=None, help="fichier HTML de sortie (defaut: dashboard_<PRODUIT>.html)")
    sp.set_defaults(func=cmd_dashboard)

    sp = sub.add_parser("select", help="definit la strategie active")
    sp.add_argument("name")
    sp.set_defaults(func=cmd_select)

    sp = sub.add_parser("backtest", help="teste la strategie sur historique")
    sp.add_argument("--days", type=int, default=365)
    with_strategy(sp)
    sp.set_defaults(func=cmd_backtest)

    sp = sub.add_parser("analyze", help="validation durcie : regimes haussier/baissier + walk-forward + sensibilite")
    sp.add_argument("--days", type=int, default=3400)
    sp.add_argument("--dd-threshold", type=float, default=0.20, dest="dd_threshold",
                    help="repli BTC qui fait basculer en marche baissier (defaut 0.20)")
    sp.add_argument("--folds", type=int, default=5, help="nb de sous-periodes walk-forward")
    with_strategy(sp)
    sp.set_defaults(func=cmd_analyze)

    sp = sub.add_parser("paper", help="trading simule sur prix reels")
    sp.add_argument("--once", action="store_true", help="un seul tick puis sortie (cron)")
    with_strategy(sp)
    sp.set_defaults(func=cmd_paper)

    sp = sub.add_parser("live", help="vrais ordres sur Coinbase")
    sp.add_argument("--once", action="store_true")
    sp.add_argument("--i-understand-live-trading", action="store_true", dest="i_understand_live_trading")
    with_strategy(sp)
    sp.set_defaults(func=cmd_live)

    sp = sub.add_parser("status", help="etat courant du bot")
    with_strategy(sp)
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("report", help="digest equity/position/trades -> console + Telegram (cron 1x/j)")
    sp.add_argument("--no-send", action="store_true", help="affiche seulement, n'envoie rien")
    sp.add_argument("--no-image", action="store_true", help="n'envoie pas le graphe d'equity")
    with_strategy(sp)
    sp.set_defaults(func=cmd_report)

    args = p.parse_args(argv)
    cfg = load_config(args.config, strategy_name=getattr(args, "strategy", None),
                      product=args.product)
    setup_logging(cfg.logging.level)
    args.func(cfg, args)


if __name__ == "__main__":
    main()
