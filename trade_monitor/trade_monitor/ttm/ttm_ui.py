from enum import Enum
import pandas as pd
import datetime as dt
from PySide2.QtCore import Qt
from trade_apl_msgs.srv import TtmMntSrv
from trade_monitor.widget_base import PandasTreeView
from trade_monitor import utility as utl
from trade_monitor.constant import INST_MSG_LIST
from trade_monitor.constant import GRAN_FREQ_DICT
from trade_monitor.constant import (FMT_DTTM_API,
                                    FMT_DATE_YMD,
                                    FMT_TIME_HM,
                                    FMT_TIME_HMS
                                    )
from trade_monitor.ttm.widget import CandlestickChartView
from trade_monitor.ttm.weekday_ui import WeekdayUi
from trade_monitor.ttm.gotoday_ui import GotodayUi
from trade_monitor.ttm.constant import ColumnName
from trade_monitor.ttm.constant import GAP_TYP_CO
from trade_monitor import ros_common as ros_com

pd.set_option("display.max_columns", 1000)
pd.set_option("display.max_rows", 300)
pd.set_option("display.width", 200)
pd.options.display.float_format = '{:.3f}'.format


class _WeekdayId(Enum):
    """
    Weekday ID.
    """
    MON = (0, "Mon")
    TUE = (1, "Tue")
    WED = (2, "Wed")
    THU = (3, "Thu")
    FRI = (4, "Fri")
    SAT = (5, "Sat")
    SUN = (6, "Sun")

    def __init__(self, id_: int, label: str):
        self.id = id_
        self.label = label

    @classmethod
    def get_member_by_id(cls, id_: int):
        for m in cls:
            if id_ == m.id:
                return m
        return None


class _GotodayId(Enum):
    """
    Gotoday ID.
    """
    NON = (0, "-")
    D05 = (1, "5")
    D10 = (2, "10")
    D15 = (3, "15")
    D20 = (4, "20")
    D25 = (5, "25")
    LSD = (6, "L/D")

    def __init__(self, id_: int, label: str):
        self.id = id_
        self.label = label

    @classmethod
    def get_member_by_id(cls, id_: int):
        for m in cls:
            if id_ == m.id:
                return m
        return None


class TtmUi():

    """
    _GAP_TYP_DICT = {
        1: "High  - Open",
        2: "Low   - Open",
        3: "Close - Open"
    }
    """

    _TREEVIEW_ITEM_DATE = "Date"
    _TREEVIEW_ITEM_WEEKDAY = "Weekday"
    _TREEVIEW_ITEM_GOTODAY = "Goto day"
    _TREEVIEW_ITEM_DATATYP = "Data type"

    _TREEVIEW_HEADERS = [
        _TREEVIEW_ITEM_DATE,
        _TREEVIEW_ITEM_WEEKDAY,
        _TREEVIEW_ITEM_GOTODAY,
        _TREEVIEW_ITEM_DATATYP
    ]

    """
    _COL_DATE = "Date"
    _COL_TIME = "Time"
    _COL_O = "O"
    _COL_H = "H"
    _COL_L = "L"
    _COL_C = "C"
    _COL_WEEKDAY_ID = "Weekday_id"
    _COL_GOTO_ID = "Goto_id"
    _COL_IS_GOTO = "Is_Goto"
    _COL_GAP_TYP = "Gap_type"
    _COL_DATA_TYP = "Data_type"
    _COL_MONTH = "Month"

    _GAP_TYP_HO = 1    # High - Open price
    _GAP_TYP_LO = 2    # Low - Open price
    _GAP_TYP_CO = 3    # Close - Open price

    _DATA_TYP_HO_MEAN = 1   # Mean of High - Open price
    _DATA_TYP_HO_STD = 2    # Std of High - Open price
    _DATA_TYP_LO_MEAN = 3   # Mean of Low - Open price
    _DATA_TYP_LO_STD = 4    # Std of Low - Open price
    _DATA_TYP_CO_MEAN = 5   # Mean of Close - Open price
    _DATA_TYP_CO_STD = 6    # Std of Close - Open price
    _DATA_TYP_CO_CSUM = 7   # Cumsum of Close - Open price
    """

    _CDL_COLUMNS = [CandlestickChartView.COL_NAME_OP,
                    CandlestickChartView.COL_NAME_HI,
                    CandlestickChartView.COL_NAME_LO,
                    CandlestickChartView.COL_NAME_CL
                    ]

    def __init__(self, ui) -> None:

        utl.remove_all_items_of_comboBox(ui.comboBox_ttm_inst)
        for obj in INST_MSG_LIST:
            ui.comboBox_ttm_inst.addItem(obj.text)

        callback = self._on_fetch_ttm_clicked
        ui.pushButton_ttm_fetch.clicked.connect(callback)

        """
        qstd_itm_mdl = QStandardItemModel()
        sel_mdl = QItemSelectionModel(qstd_itm_mdl)

        callback = self._on_selection_ttm_changed
        sel_mdl.selectionChanged.connect(callback)
        """

        callback = self._on_ttm_weekday_clicked
        ui.pushButton_ttm_weekday.clicked.connect(callback)

        callback = self._on_ttm_gotoday_clicked
        ui.pushButton_ttm_gotoday.clicked.connect(callback)

        # set Tree View
        pdtreeview = PandasTreeView(ui.widget_TreeView_ttm)

        selmdl = pdtreeview.selectionModel()
        callback = self._on_selection_ttm_changed
        selmdl.selectionChanged.connect(callback)

        header = pdtreeview.header()
        callback = self._on_view_header_sectionClicked
        header.sectionClicked.connect(callback)

        chartview = CandlestickChartView(ui.widget_ChartView_ttm)

        # Create service client "ttm_monitor"
        srv_type = TtmMntSrv
        srv_name = "ttm_monitor"
        srv_cli_list = []
        for obj in INST_MSG_LIST:
            fullname = obj.namespace + "/" + srv_name
            srv_cli = ros_com.get_node().create_client(srv_type, fullname)
            srv_cli_list.append(srv_cli)

        self._weekday_ui = WeekdayUi()
        self._gotoday_ui = GotodayUi()

        # self._qstd_itm_mdl = qstd_itm_mdl
        self._chartview = chartview

        self._ui = ui
        self._pdtreeview = pdtreeview
        self._gran_id = 0
        self._srv_cli_list = srv_cli_list
        self._logger = ros_com.get_logger()

    def _on_view_header_sectionClicked(self, logical_index):
        self._pdtreeview.show_header_menu(logical_index)

    def _on_fetch_ttm_clicked(self):
        inst_idx = self._ui.comboBox_ttm_inst.currentIndex()
        inst_msg = INST_MSG_LIST[inst_idx]

        # fetch TTM data
        req = TtmMntSrv.Request()

        srv_cli = self._srv_cli_list[inst_idx]
        if not srv_cli.service_is_ready():
            self._logger.error("service server [{}] not to become ready"
                               .format(inst_msg.text))
        else:

            rsp = ros_com.call_servive_sync(srv_cli, req, timeout_sec=10.0)
            self._gran_id = rsp.gran_id

            start_time_str = rsp.start_time
            end_time_str = rsp.end_time
            freq = GRAN_FREQ_DICT[rsp.gran_id]
            time_range_list = pd.date_range(start_time_str,
                                            end_time_str,
                                            freq=freq
                                            ).strftime(FMT_TIME_HM).to_list()

            # ---------- compose Table "OHLC" ----------
            tbl = []
            for rec in rsp.ttm_tbl_ohlc:
                record = [rec.date,
                          rec.time,
                          rec.open,
                          rec.high,
                          rec.low,
                          rec.close
                          ]
                tbl.append(record)

            columns = [ColumnName.DATE.value,
                       ColumnName.TIME.value,
                       ColumnName.CDL_O.value,
                       ColumnName.CDL_H.value,
                       ColumnName.CDL_L.value,
                       ColumnName.CDL_C.value,
                       ]
            df_ohlc = pd.DataFrame(tbl, columns=columns)

            index = [ColumnName.DATE.value,
                     ColumnName.TIME.value
                     ]
            df_ohlc.set_index(index, inplace=True)

            # ---------- compose Table "Base" ----------
            tbl = []
            for rec in rsp.ttm_tbl_base:
                record = [rec.date,
                          rec.month,
                          rec.weekday_id,
                          rec.goto_id,
                          rec.is_goto,
                          rec.gap_type
                          ] + rec.data_list.tolist()
                tbl.append(record)

            columns = [ColumnName.DATE.value,
                       ColumnName.MONTH.value,
                       ColumnName.WEEKDAY_ID.value,
                       ColumnName.GOTO_ID.value,
                       ColumnName.IS_GOTO.value,
                       ColumnName.GAP_TYP.value
                       ] + time_range_list
            df_base = pd.DataFrame(tbl, columns=columns)

            index = [ColumnName.DATE.value,
                     ColumnName.MONTH.value,
                     ColumnName.WEEKDAY_ID.value,
                     ColumnName.GOTO_ID.value,
                     ColumnName.IS_GOTO.value,
                     ColumnName.GAP_TYP.value,
                     ]
            df_base.set_index(index, inplace=True)

            # ---------- compose Table "week_goto" ----------
            """
            level = [ColumnName.WEEKDAY_ID,
                     ColumnName.IS_GOTO,
                     ColumnName.GAP_TYP,
                     ]
            df_week_goto = self.__make_statistics_dataframe(df_base, level)
            """
            """
            df_week_goto = ttmcom.convert_base2weekgoto(df_base)
            """

            # ---------- compose Table "month_goto" ----------
            """
            level = [ColumnName.MONTH,
                     ColumnName.GOTO_ID,
                     ColumnName.GAP_TYP,
                     ]
            df_month_goto = self.__make_statistics_dataframe(df_base, level)
            """
            """
            df_month_goto = ttmcom.convert_base2monthgoto(df_base)
            """

            # ---------- compose Tree View ----------
            flg = df_base.index.get_level_values(ColumnName.GAP_TYP.value) == GAP_TYP_CO
            """
            df = df_base[flg]
            for index, row in df.iterrows():
                items = [
                    QStandardItem(index[0]),  # date
                    QStandardItem(WEEKDAY_ID_DICT[index[2]]),
                    QStandardItem(GOTODAY_ID_DICT[index[3]]),
                ]
                self._qstd_itm_mdl.appendRow(items)
            """
            tbl = []
            for index, row in df_base[flg].iterrows():
                wdmem = _WeekdayId.get_member_by_id(index[2])
                gdmem = _GotodayId.get_member_by_id(index[3])
                items = [
                    index[0],  # date
                    # WEEKDAY_ID_DICT[index[2]],
                    wdmem.label,
                    gdmem.label,
                    0
                ]
                tbl.append(items)
            df = pd.DataFrame(tbl,
                              columns=self._TREEVIEW_HEADERS)
            df.set_index([self._TREEVIEW_ITEM_DATE], inplace=True)

            self._pdtreeview.set_dataframe(df)
            selmdl = self._pdtreeview.selectionModel()
            callback = self._on_selection_ttm_changed
            selmdl.selectionChanged.connect(callback)

            self._df_ohlc = df_ohlc
            self._df_base = df_base

            self._ui.pushButton_ttm_weekday.setEnabled(True)
            self._ui.pushButton_ttm_gotoday.setEnabled(True)
            """
            self._df_week_goto = df_week_goto
            self._df_month_goto = df_month_goto
            """

    def _on_selection_ttm_changed(self, selected, _):

        if not selected.isEmpty():

            model_index = selected.at(0).indexes()[0]
            r = model_index.row()
            proxy = self._pdtreeview.proxy
            date_str = proxy.index(r, 0, model_index).data(role=Qt.UserRole)

            df_ohlc = self._df_ohlc
            flg = df_ohlc.index.get_level_values(ColumnName.DATE.value) == date_str
            df = df_ohlc[flg].reset_index(level=ColumnName.DATE.value, drop=True)
            fmt = FMT_DATE_YMD + FMT_TIME_HM
            df = df.rename(index=lambda t: dt.datetime.strptime(date_str + t, fmt))
            df.columns = self._CDL_COLUMNS

            max_y = df[CandlestickChartView.COL_NAME_HI].max()
            min_y = df[CandlestickChartView.COL_NAME_LO].min()
            dif = (max_y - min_y) * 0.05
            self._chartview.set_max_y(max_y + dif)
            self._chartview.set_min_y(min_y - dif)

            inst_idx = self._ui.comboBox_ttm_inst.currentIndex()
            decimal_digit = INST_MSG_LIST[inst_idx].decimal_digit

            self._chartview.update(df, self._gran_id, decimal_digit)
            self._ui.widget_ChartView_ttm.setEnabled(True)

    def _on_ttm_weekday_clicked(self):

        inst_idx = self._ui.comboBox_ttm_inst.currentIndex()
        decimal_digit = INST_MSG_LIST[inst_idx].decimal_digit

        df = self._get_dataframe()

        self._weekday_ui.show()
        self._weekday_ui.init_resize()
        self._weekday_ui.set_data(df,
                                  self._gran_id,
                                  decimal_digit)

    def _on_ttm_gotoday_clicked(self):

        inst_idx = self._ui.comboBox_ttm_inst.currentIndex()
        decimal_digit = INST_MSG_LIST[inst_idx].decimal_digit

        df = self._get_dataframe()

        self._gotoday_ui.show()
        self._gotoday_ui.init_resize()
        self._gotoday_ui.set_data(df,
                                  self._gran_id,
                                  decimal_digit)

    def _get_dataframe(self):

        is_selected = self._pdtreeview.is_selected()
        dftv = self._pdtreeview.get_dataframe(is_selected=is_selected)

        date_list = sorted(dftv.index.to_list())
        df = self._df_base.loc[(date_list), :]

        return df

    """
    def __make_statistics_dataframe(self,
                                    df_base: pd.DataFrame,
                                    level: list
                                    ) -> pd.DataFrame:

        # ----- make DataFrame "Mean" -----
        df_mean = df_base.mean(level=level).sort_index()
        df_mean.reset_index(COL_GAP_TYP, inplace=True)

        df_mean[COL_DATA_TYP] = 0
        cond = df_mean[COL_GAP_TYP] == self._GAP_TYP_HO
        df_mean.loc[cond, COL_DATA_TYP] = self._DATA_TYP_HO_MEAN
        cond = df_mean[COL_GAP_TYP] == self._GAP_TYP_LO
        df_mean.loc[cond, COL_DATA_TYP] = self._DATA_TYP_LO_MEAN
        cond = df_mean[COL_GAP_TYP] == self._GAP_TYP_CO
        df_mean.loc[cond, COL_DATA_TYP] = self._DATA_TYP_CO_MEAN

        df_mean.drop(columns=COL_GAP_TYP, inplace=True)
        index = COL_DATA_TYP
        df_mean.set_index(index, append=True, inplace=True)

        # ----- make DataFrame "Std" -----
        df_std = df_base.std(level=level).sort_index()
        df_std.reset_index(COL_GAP_TYP, inplace=True)

        df_std[COL_DATA_TYP] = 0
        cond = df_std[COL_GAP_TYP] == self._GAP_TYP_HO
        df_std.loc[cond, COL_DATA_TYP] = self._DATA_TYP_HO_STD
        cond = df_std[COL_GAP_TYP] == self._GAP_TYP_LO
        df_std.loc[cond, COL_DATA_TYP] = self._DATA_TYP_LO_STD
        cond = df_std[COL_GAP_TYP] == self._GAP_TYP_CO
        df_std.loc[cond, COL_DATA_TYP] = self._DATA_TYP_CO_STD

        df_std.drop(columns=COL_GAP_TYP, inplace=True)
        index = COL_DATA_TYP
        df_std.set_index(index, append=True, inplace=True)

        # ----- make DataFrame "Cumulative Sum" -----
        cond = df_mean.index.get_level_values(COL_DATA_TYP) == self._DATA_TYP_CO_MEAN
        df_csum = df_mean[cond].rename(index={self._DATA_TYP_CO_MEAN: self._DATA_TYP_CO_CSUM},
                                       level=COL_DATA_TYP)
        df_csum = df_csum.cumsum(axis=1)

        # concat "df_mean" and "df_std" and "df_csum"
        return pd.concat([df_mean, df_std, df_csum]).sort_index()
        """
