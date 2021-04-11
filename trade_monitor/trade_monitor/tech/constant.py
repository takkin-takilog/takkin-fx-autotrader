from enum import Enum, IntEnum, auto
from dataclasses import dataclass
from trade_monitor.constant import InstParam, GranParam

VALID_INST_LIST = [
    InstParam.USDJPY,
    InstParam.EURJPY,
    InstParam.EURUSD
]

VALID_GRAN_LIST = [
    GranParam.D,
    GranParam.H1,
    GranParam.M10,
    GranParam.M1,
]


class ColNameOhlc(Enum):
    """
    Pandas OHLC dataframe column name.
    """
    DATETIME = "datetime"
    # ---------- OHLC ----------
    MID_O = "mid_o"
    MID_H = "mid_h"
    MID_L = "mid_l"
    MID_C = "mid_c"

    @classmethod
    def to_list(cls):
        return [m.value for m in cls]


class ColNameTrnd(Enum):
    """
    Pandas Trend dataframe column name.
    """
    # ---------- MA(Moving Average) ----------
    SMA_S = "sma_s"
    SMA_M = "sma_m"
    SMA_L = "sma_l"
    EMA_S = "ema_s"
    EMA_M = "ema_m"
    EMA_L = "ema_l"
    WMA_S = "wma_s"
    WMA_M = "wma_m"
    WMA_L = "wma_l"
    # ---------- Ichimoku Kinko ----------
    ICHMK_BASE = "ichmk_base"
    ICHMK_CONV = "ichmk_conv"
    ICHMK_SPNA = "ichmk_sapn_a"
    ICHMK_SPNB = "ichmk_sapn_b"
    ICHMK_LAG = "ichmk_lag"
    # ---------- Bollinger Bands ----------
    BLNGR_BASE = "blngr_base"
    BLNGR_ps1 = "blngr_ps1"
    BLNGR_ps2 = "blngr_ps2"
    BLNGR_ps3 = "blngr_ps3"
    BLNGR_ns1 = "blngr_ns1"
    BLNGR_ns2 = "blngr_ns2"
    BLNGR_ns3 = "blngr_ns3"

    @classmethod
    def to_list(cls):
        return [m.value for m in cls]


class ColNameOsci(Enum):
    """
    Pandas Oscillator dataframe column name.
    """
    # ---------- RSI ----------
    RSI_SMA = "rsi_sma"
    RSI_EMA = "rsi_ema"
    # ---------- MACD ----------
    MACD_MACD = "macd_macd"
    MACD_SIG = "macd_sig"
    # ---------- Stochastics ----------
    STCHA_K = "stcha_k"
    STCHA_D = "stcha_d"
    STCHA_SD = "stcha_sd"

    @classmethod
    def to_list(cls):
        return [m.value for m in cls]


class ColNameSma(Enum):
    """
    Pandas SMA(Simple Moving Average) dataframe column name.
    """
    DATETIME = "datetime"
    CRS_TYP = "cross_type"
    CRS_LVL = "cross_level"
    ANG_S = "angle_s"
    ANG_M = "angle_m"
    ANG_L = "angle_l"

    @classmethod
    def to_list(cls):
        return [m.value for m in cls]


class ColNameLine(Enum):
    """
    Line Chart dataframe column name.
    """
    DATA_TYP = "data_type"
    PEN = "pen"
    SERIES = "series"

    @classmethod
    def to_list(cls):
        return [m.value for m in cls]
