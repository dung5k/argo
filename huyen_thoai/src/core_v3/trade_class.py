from enum import IntEnum

class TradeClass(IntEnum):
    """
    Unified label mapping for Trade Actions.
    Used consistently across Training, Inference, and the Trading Bot.
    """
    SELL = 0
    BUY = 1
    SIDEWAY = 2
