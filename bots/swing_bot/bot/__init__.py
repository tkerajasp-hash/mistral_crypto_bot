"""Bot de trading swing pour Coinbase Advanced Trade.

Objectifs :
- suivre les vraies tendances haussieres (filtre de regime + cassure + ADX)
- proteger le capital avec un stop loss initial ATR + un stop suiveur "chandelier"
- minimiser les frais (ordres maker post-only, une decision par bougie, cooldown)
"""

__version__ = "0.1.0"
