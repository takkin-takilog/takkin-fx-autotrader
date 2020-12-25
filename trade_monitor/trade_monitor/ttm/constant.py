from enum import Enum, IntEnum


class ColumnName(Enum):
    """
    Pandas dataframe column name.
    """
    DATE = "Date"
    TIME = "Time"
    CDL_O = "O"
    CDL_H = "H"
    CDL_L = "L"
    CDL_C = "C"
    WEEKDAY_ID = "Weekday_id"
    GOTO_ID = "Goto_id"
    IS_GOTO = "Is_Goto"
    GAP_TYP = "Gap_type"
    DATA_TYP = "Data_type"
    MONTH = "Month"


class GapType(IntEnum):
    """
    Gap type.
    """
    HO = 1    # High - Open price
    LO = 2    # Low - Open price
    CO = 3    # Close - Open price


class DataType(IntEnum):
    """
    Data type.
    """
    HO_MEAN = 1   # Mean of High - Open price
    HO_STD = 2    # Std of High - Open price
    LO_MEAN = 3   # Mean of Low - Open price
    LO_STD = 4    # Std of Low - Open price
    CO_MEAN = 5   # Mean of Close - Open price
    CO_STD = 6    # Std of Close - Open price
    CO_CSUM = 7   # Cumsum of Close - Open price