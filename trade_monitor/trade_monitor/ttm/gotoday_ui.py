from enum import Enum, IntEnum, auto
import pandas as pd
from PySide2.QtWidgets import QHeaderView
from PySide2.QtWidgets import QTableWidgetItem
from PySide2.QtCore import QDate, Qt
from PySide2.QtGui import QColor, QBrush
from trade_monitor import ros_common as ros_com
from trade_monitor.constant import FMT_QT_DATE_YMD
from trade_monitor.constant import GranParam, InstParam
from trade_monitor.utility import DateRangeManager
from trade_monitor.ttm.constant import ColumnName
from trade_monitor.ttm.constant import DataType
from trade_monitor.ttm.widget import LineChartViewStats
from trade_monitor.ttm.widget import LineChartViewCumsum
from trade_monitor.ttm.widget import BaseUi
from trade_monitor.ttm.constant import AnalysisType, ChartTag
from trade_apl_msgs.msg import TtmTblBaseRecMsg as BsMsg


class _GotodayId(Enum):
    """
    Gotoday ID.
    """
    NTD = (BsMsg.GOTODAY_NONE, "Not", QColor(Qt.black), "#f5dcdc")
    D05 = (BsMsg.GOTODAY_D05, "5Day", QColor(Qt.black), "#d9ead3")
    D10 = (BsMsg.GOTODAY_D10, "10Day", QColor(Qt.black), "#fce5cd")
    D15 = (BsMsg.GOTODAY_D15, "15Day", QColor(Qt.black), "#cfe2f3")
    D20 = (BsMsg.GOTODAY_D20, "20Day", QColor(Qt.black), "#fff2cc")
    D25 = (BsMsg.GOTODAY_D25, "25Day", QColor(Qt.black), "#ead1dc")
    LSD = (BsMsg.GOTODAY_DLST, "LstDay", QColor(Qt.black), "#d0e0e3")

    def __init__(self,
                 id_: int,
                 text: str,
                 foreground_color: QColor,
                 background_color: QColor
                 ) -> None:
        self.id = id_
        self.text = text
        self.foreground_color = QBrush(QColor(foreground_color))
        self.background_color = QBrush(QColor(background_color))


class _ChartType(Enum):
    """
    Chart type.
    """
    STATS = "Stats"
    CUMSUM = "CumSum"

    def __init__(self,
                 text: str,
                 ) -> None:
        self.text = text


class _TblColPos(IntEnum):
    """
    Table Column Position.
    """
    GOTODAY = 0
    CHARTTYP = auto()
    CHARTVIEW = auto()


class GotodayUi(BaseUi):

    def __init__(self, parent=None):
        super().__init__(parent)

        ui = self._load_ui(parent, "gotoday.ui")
        self.setCentralWidget(ui)
        self.resize(ui.frameSize())

        self.setWindowTitle("TTM Gotoday")

        callback = self._on_pushButton_update_clicked
        ui.pushButton_update.clicked.connect(callback)
        callback = self._on_checkBox_autoupdate_stateChanged
        ui.checkBox_AutoUpdate.stateChanged.connect(callback)
        callback = self._on_lower_date_changed
        ui.dateEdit_lower.dateChanged.connect(callback)
        callback = self._on_upper_date_changed
        ui.dateEdit_upper.dateChanged.connect(callback)
        callback = self._on_spinBox_step_value_changed
        ui.spinBox_Step.valueChanged.connect(callback)
        callback = self._on_ScrollBar_DateRange_value_changed
        ui.ScrollBar_DateRange.valueChanged.connect(callback)

        callback = self._on_checkBox_ShowItem_stateChanged
        ui.checkBox_ChartTyp_stat.stateChanged.connect(callback)
        callback = self._on_checkBox_ShowItem_stateChanged
        ui.checkBox_ChartTyp_cumsum.stateChanged.connect(callback)

        callback = self._on_checkBox_ShowItem_stateChanged
        ui.checkBox_GotoDayTyp_Nd.stateChanged.connect(callback)
        callback = self._on_checkBox_ShowItem_stateChanged
        ui.checkBox_GotoDayTyp_5d.stateChanged.connect(callback)
        callback = self._on_checkBox_ShowItem_stateChanged
        ui.checkBox_GotoDayTyp_10d.stateChanged.connect(callback)
        callback = self._on_checkBox_ShowItem_stateChanged
        ui.checkBox_GotoDayTyp_15d.stateChanged.connect(callback)
        callback = self._on_checkBox_ShowItem_stateChanged
        ui.checkBox_GotoDayTyp_20d.stateChanged.connect(callback)
        callback = self._on_checkBox_ShowItem_stateChanged
        ui.checkBox_GotoDayTyp_25d.stateChanged.connect(callback)
        callback = self._on_checkBox_ShowItem_stateChanged
        ui.checkBox_GotoDayTyp_Ld.stateChanged.connect(callback)

        row_cnt = ui.tableWidget.rowCount()
        for i in reversed(range(row_cnt)):
            ui.tableWidget.removeRow(i)

        col_cnt = ui.tableWidget.columnCount()
        header = ui.tableWidget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        for i in range(col_cnt - 1):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        vHeaderView = ui.tableWidget.verticalHeader()
        # hHeaderView = ui.tableWidget.horizontalHeader()
        vHeaderView.setDefaultSectionSize(300)

        callback = self._on_vHeaderView_sectionResized
        vHeaderView.sectionResized.connect(callback)

        self._CHECKSTATE_GOTODAYTYP_DICT = {
            _GotodayId.NTD: ui.checkBox_GotoDayTyp_Nd.checkState,
            _GotodayId.D05: ui.checkBox_GotoDayTyp_5d.checkState,
            _GotodayId.D10: ui.checkBox_GotoDayTyp_10d.checkState,
            _GotodayId.D15: ui.checkBox_GotoDayTyp_15d.checkState,
            _GotodayId.D20: ui.checkBox_GotoDayTyp_20d.checkState,
            _GotodayId.D25: ui.checkBox_GotoDayTyp_25d.checkState,
            _GotodayId.LSD: ui.checkBox_GotoDayTyp_Ld.checkState
        }

        self._CHECKSTATE_CHARTTYP_DICT = {
            _ChartType.STATS: ui.checkBox_ChartTyp_stat.checkState,
            _ChartType.CUMSUM: ui.checkBox_ChartTyp_cumsum.checkState,
        }

        self._drm = DateRangeManager()
        self._logger = ros_com.get_logger()
        self._ui = ui
        self._df_base = pd.DataFrame()
        self._gran_param = GranParam.D
        self._inst_param = InstParam.USDJPY
        self._chart_idx_list = []
        self._is_require_reconstruct_table = True

    def set_data(self,
                 df_base: pd.DataFrame,
                 gran_param: GranParam,
                 inst_param: InstParam):

        date_list = list(df_base.groupby(ColumnName.DATE.value).groups.keys())

        self._drm.init_date_list(date_list)

        qdate_l = QDate.fromString(self._drm.lower_date, FMT_QT_DATE_YMD)
        qdate_u = QDate.fromString(self._drm.upper_date, FMT_QT_DATE_YMD)

        self._df_base = df_base
        self._gran_param = gran_param
        self._inst_param = inst_param

        wasBlocked1 = self._ui.dateEdit_lower.blockSignals(True)
        wasBlocked2 = self._ui.dateEdit_upper.blockSignals(True)
        wasBlocked3 = self._ui.spinBox_Step.blockSignals(True)
        wasBlocked4 = self._ui.ScrollBar_DateRange.blockSignals(True)

        self._ui.dateEdit_lower.setDateRange(qdate_l, qdate_u)
        self._ui.dateEdit_lower.setDate(qdate_l)
        self._ui.dateEdit_upper.setDateRange(qdate_l, qdate_u)
        self._ui.dateEdit_upper.setDate(qdate_u)
        self._ui.spinBox_Step.setMinimum(1)
        self._ui.spinBox_Step.setMaximum(self._drm.length)
        self._ui.spinBox_Step.setValue(self._drm.length)
        self._ui.ScrollBar_DateRange.setMaximum(self._drm.slidable_count)
        self._ui.ScrollBar_DateRange.setValue(self._drm.lower_pos)

        self._ui.dateEdit_lower.blockSignals(wasBlocked1)
        self._ui.dateEdit_upper.blockSignals(wasBlocked2)
        self._ui.spinBox_Step.blockSignals(wasBlocked3)
        self._ui.ScrollBar_DateRange.blockSignals(wasBlocked4)

    def _on_vHeaderView_sectionResized(self, index, oldSize, newSize):
        # self._logger.debug("--- on_tableWidget_rowResized ----------")

        vHeaderView = self._ui.tableWidget.verticalHeader()
        vHeaderView.setDefaultSectionSize(newSize)

    def _on_pushButton_update_clicked(self, checked):
        self._update_table()

    def _on_checkBox_autoupdate_stateChanged(self, state):
        # self._logger.debug("---on_checkBox_autoupdate_stateChanged ----------")
        # self._logger.debug("state:{}".format(state))

        if state == Qt.Checked:
            self._ui.pushButton_update.setEnabled(False)
            if self._is_require_reconstruct_table:
                self._update_table()
        else:
            self._ui.pushButton_update.setEnabled(True)

    def _on_lower_date_changed(self, qdate):
        # self._logger.debug("---[1]on_start_date_changed ----------")

        sdt_str = qdate.toString(FMT_QT_DATE_YMD)
        self._drm.set_lower(sdt_str)

        stat = self._ui.checkBox_AutoUpdate.checkState()
        if stat == Qt.Checked:
            self._update_table()

        wasBlocked1 = self._ui.dateEdit_upper.blockSignals(True)
        wasBlocked2 = self._ui.spinBox_Step.blockSignals(True)
        wasBlocked3 = self._ui.ScrollBar_DateRange.blockSignals(True)

        self._ui.dateEdit_upper.setMinimumDate(qdate)
        self._ui.spinBox_Step.setValue(self._drm.count)
        self._ui.ScrollBar_DateRange.setMaximum(self._drm.slidable_count)
        self._ui.ScrollBar_DateRange.setValue(self._drm.lower_pos)

        self._ui.dateEdit_upper.blockSignals(wasBlocked1)
        self._ui.spinBox_Step.blockSignals(wasBlocked2)
        self._ui.ScrollBar_DateRange.blockSignals(wasBlocked3)

    def _on_upper_date_changed(self, qdate):
        # self._logger.debug("---[2]on_end_date_changed ----------")

        sdt_str = qdate.toString(FMT_QT_DATE_YMD)
        self._drm.set_upper(sdt_str)

        stat = self._ui.checkBox_AutoUpdate.checkState()
        if stat == Qt.Checked:
            self._update_table()

        wasBlocked1 = self._ui.dateEdit_lower.blockSignals(True)
        wasBlocked2 = self._ui.spinBox_Step.blockSignals(True)
        wasBlocked3 = self._ui.ScrollBar_DateRange.blockSignals(True)

        self._ui.dateEdit_lower.setMaximumDate(qdate)
        self._ui.spinBox_Step.setValue(self._drm.count)
        self._ui.ScrollBar_DateRange.setMaximum(self._drm.slidable_count)
        self._ui.ScrollBar_DateRange.setValue(self._drm.lower_pos)

        self._ui.dateEdit_lower.blockSignals(wasBlocked1)
        self._ui.spinBox_Step.blockSignals(wasBlocked2)
        self._ui.ScrollBar_DateRange.blockSignals(wasBlocked3)

    def _on_spinBox_step_value_changed(self, value):
        # self._logger.debug("---[3]on_spinBox_step_value_changed ----------")

        slide_cnt = value - self._drm.count

        if 0 < slide_cnt:
            self._drm.expand_range(slide_cnt)
        else:
            self._drm.shrink_range(-slide_cnt)

        stat = self._ui.checkBox_AutoUpdate.checkState()
        if stat == Qt.Checked:
            self._update_table()

        qdate_l = QDate.fromString(self._drm.lower_date, FMT_QT_DATE_YMD)
        qdate_u = QDate.fromString(self._drm.upper_date, FMT_QT_DATE_YMD)

        wasBlocked1 = self._ui.dateEdit_lower.blockSignals(True)
        wasBlocked2 = self._ui.dateEdit_upper.blockSignals(True)
        wasBlocked3 = self._ui.ScrollBar_DateRange.blockSignals(True)

        self._ui.dateEdit_lower.setMaximumDate(qdate_u)
        self._ui.dateEdit_lower.setDate(qdate_l)
        self._ui.dateEdit_upper.setMinimumDate(qdate_l)
        self._ui.dateEdit_upper.setDate(qdate_u)
        self._ui.ScrollBar_DateRange.setMaximum(self._drm.slidable_count)
        self._ui.ScrollBar_DateRange.setValue(self._drm.lower_pos)

        self._ui.dateEdit_lower.blockSignals(wasBlocked1)
        self._ui.dateEdit_upper.blockSignals(wasBlocked2)
        self._ui.ScrollBar_DateRange.blockSignals(wasBlocked3)

    def _on_ScrollBar_DateRange_value_changed(self, value):
        # self._logger.debug("---[4]on_ScrollBar_DateRange_value_changed ----------")

        step = value - self._drm.lower_pos
        self._drm.slide(step)

        stat = self._ui.checkBox_AutoUpdate.checkState()
        if stat == Qt.Checked:
            self._update_table()

        qdate_l = QDate.fromString(self._drm.lower_date, FMT_QT_DATE_YMD)
        qdate_u = QDate.fromString(self._drm.upper_date, FMT_QT_DATE_YMD)

        wasBlocked1 = self._ui.dateEdit_lower.blockSignals(True)
        wasBlocked2 = self._ui.dateEdit_upper.blockSignals(True)

        self._ui.dateEdit_lower.setMaximumDate(qdate_u)
        self._ui.dateEdit_lower.setDate(qdate_l)
        self._ui.dateEdit_upper.setMinimumDate(qdate_l)
        self._ui.dateEdit_upper.setDate(qdate_u)

        self._ui.dateEdit_lower.blockSignals(wasBlocked1)
        self._ui.dateEdit_upper.blockSignals(wasBlocked2)

    def _on_checkBox_ShowItem_stateChanged(self, state):
        # self._logger.debug("--- on_checkBox_ShowItem_stateChanged ----------")

        self._is_require_reconstruct_table = True

        stat = self._ui.checkBox_AutoUpdate.checkState()
        if stat == Qt.Checked:
            self._update_table()

    def _update_table(self):

        df_base = self._get_latest_dataframe()

        if self._is_require_reconstruct_table:
            self._reconstruct_table()

        self._update_chart(df_base)

    def _get_latest_dataframe(self):
        # self._logger.debug("---[99]update_dataframe ----------")

        sdt_str = self._drm.lower_date
        sdt_end = self._drm.upper_date
        mst_list = self._df_base.index.get_level_values(level=ColumnName.DATE.value)
        df_base = self._df_base[(sdt_str <= mst_list) & (mst_list <= sdt_end)]
        return df_base

    def _generate_dfgotoday_from_dfbase(self,
                                        df_base: pd.DataFrame
                                        ) -> pd.DataFrame:

        level = [ColumnName.GOTODAY_ID.value,
                 ColumnName.GAP_TYP.value
                 ]
        return self._generate_statistics_dataframe(df_base, level)

    def _reconstruct_table(self):

        row_cnt = self._ui.tableWidget.rowCount()
        for i in reversed(range(row_cnt)):
            self._ui.tableWidget.removeRow(i)

        chart_idx_list = []
        for gotoday_m in _GotodayId:
            checkState = self._CHECKSTATE_GOTODAYTYP_DICT[gotoday_m]
            wd_stat = checkState()
            if wd_stat != Qt.Checked:
                continue

            for charttyp_m in _ChartType:
                checkState = self._CHECKSTATE_CHARTTYP_DICT[charttyp_m]
                gd_stat = checkState()
                if gd_stat != Qt.Checked:
                    continue

                chart_idx_list.append([gotoday_m, charttyp_m])

        for i, chart_idx in enumerate(chart_idx_list):
            gotoday_m = chart_idx[0]
            charttyp_m = chart_idx[1]

            self._ui.tableWidget.insertRow(i)

            # set Table Item "Goto-Day Type"
            back_color = gotoday_m.background_color
            item_wd = QTableWidgetItem(gotoday_m.text)
            item_wd.setTextAlignment(Qt.AlignCenter)
            item_wd.setForeground(gotoday_m.foreground_color)
            item_wd.setBackground(back_color)
            pos = _TblColPos.GOTODAY.value
            self._ui.tableWidget.setItem(i, pos, item_wd)

            # set Table Item "Chart Type"
            item_ct = QTableWidgetItem(charttyp_m.text)
            item_ct.setTextAlignment(Qt.AlignCenter)
            item_ct.setBackground(back_color)
            pos = _TblColPos.CHARTTYP.value
            self._ui.tableWidget.setItem(i, pos, item_ct)

            # set Table Item "Chart View"
            if charttyp_m == _ChartType.STATS:
                tag = ChartTag(
                    analysis_type=AnalysisType.GOTODAY,
                    gotoday=gotoday_m.text
                )
                chartview = LineChartViewStats(tag)
            else:
                chartview = LineChartViewCumsum()
            chartview.chart().setBackgroundBrush(back_color)
            pos = _TblColPos.CHARTVIEW.value
            self._ui.tableWidget.setCellWidget(i, pos, chartview)

        self._chart_idx_list = chart_idx_list
        self._is_require_reconstruct_table = False

    def _update_chart(self, df_base):

        df = self._generate_dfgotoday_from_dfbase(df_base)
        df_base_r = self._reconstruct_dataframe_base(df_base)

        mst_list = df.index.get_level_values(level=ColumnName.DATA_TYP.value)
        df_stats = df[mst_list < DataType.CO_CSUM.value]

        cond = ((mst_list == DataType.CO_MEAN.value) |
                (mst_list == DataType.HO_MEAN.value) |
                (mst_list == DataType.LO_MEAN.value))
        df_stats_max = df[cond]

        max_ = df_stats_max.max().max()
        min_ = df_stats_max.min().min()
        stats_max = max(abs(max_), abs(min_))

        df_csum = df[mst_list == DataType.CO_CSUM.value]
        max_ = df_csum.max().max()
        min_ = df_csum.min().min()
        csum_max = max(abs(max_), abs(min_))

        for i, chart_idx in enumerate(self._chart_idx_list):
            gotoday_m = chart_idx[0]
            charttyp_m = chart_idx[1]

            if charttyp_m == _ChartType.STATS:
                df_trg = df_stats
                max_y = stats_max
            else:
                df_trg = df_csum
                max_y = csum_max

            chartview = self._ui.tableWidget.cellWidget(i, _TblColPos.CHARTVIEW)
            chartview.set_max_y(max_y)
            chartview.set_min_y(-max_y)
            idxloc = gotoday_m.id
            if idxloc in df_trg.index:
                chartview.update(df_trg.loc[idxloc], self._gran_param, self._inst_param)
                level = [ColumnName.GOTODAY_ID.value]
                df_date = df_base_r.xs([idxloc], level=level)
                chartview.set_dataframe_date(df_date)
            else:
                chartview.clear()

    def _reconstruct_dataframe_base(self, df_base):

        df_base_r = df_base.reset_index()
        columns = [ColumnName.WEEKDAY_ID.value,
                   ColumnName.IS_GOTO.value]
        df_base_r.drop(columns=columns, inplace=True)
        index = [ColumnName.GOTODAY_ID.value,
                 ColumnName.DATE.value,
                 ColumnName.GAP_TYP.value]
        df_base_r.set_index(index, inplace=True)
        df_base_r.sort_index(inplace=True)

        return df_base_r

    def resizeEvent(self, event):
        super().resizeEvent(event)
