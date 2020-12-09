import os
import pandas as pd
from PySide2.QtWidgets import QMainWindow, QHeaderView
from PySide2.QtWidgets import QTableWidgetItem
from PySide2.QtCore import QFile, QDate, Qt
from PySide2.QtUiTools import QUiLoader
from trade_monitor import utilities as utl
from trade_monitor.utilities import FMT_QT_DATE_YMD
from trade_monitor.utilities import DateRangeManager
from trade_monitor.ttm.ttm_common import COL_DATE, COL_DATA_TYP, DATA_TYP_CO_CSUM
from trade_monitor.ttm.ttm_common import (WEEKDAY_ID_MON,
                                          WEEKDAY_ID_TUE,
                                          WEEKDAY_ID_WED,
                                          WEEKDAY_ID_THU,
                                          WEEKDAY_ID_FRI)
from trade_monitor.ttm.chart import LineChartTtmStatistics
from trade_monitor.ttm.chart import LineChartTtmCumsum
from trade_monitor.ttm import ttm_common as ttmcom


class TtmDetails(QMainWindow):

    _COL_WEEKDAY_ID = "Weekday_id"
    _COL_IS_GOTO = "Is_Goto"
    _COL_CHART_TYP = "Chart_type"
    _COL_TBLPOS = "TblPos_Row"
    _COL_CHART_OBJ = "Chart_Obj"

    # define Goto-Day ID
    _GOTODAY_ID_T = 0
    _GOTODAY_ID_F = 1

    # define Chart Type
    _CHART_TYP_STATISTICS = 0
    _CHART_TYP_CUMSUM = 1

    _WEEKDAY_ID_DICT = {
        WEEKDAY_ID_MON: "Mon",
        WEEKDAY_ID_TUE: "Tue",
        WEEKDAY_ID_WED: "Wed",
        WEEKDAY_ID_THU: "Thu",
        WEEKDAY_ID_FRI: "Fri",
    }

    _GOTO_ID_DICT = {
        _GOTODAY_ID_T: "T",
        _GOTODAY_ID_F: "F"
    }

    _CHARTTYP_LIST = {
        _CHART_TYP_STATISTICS,
        _CHART_TYP_CUMSUM
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        ui = self._load_ui(parent)
        self.setCentralWidget(ui)
        self.resize(ui.frameSize())

        self.setWindowTitle("TTM Details")

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
        ui.checkBox_GotoDay_true.stateChanged.connect(callback)
        callback = self._on_checkBox_ShowItem_stateChanged
        ui.checkBox_GotoDay_false.stateChanged.connect(callback)

        callback = self._on_checkBox_ShowItem_stateChanged
        ui.checkBox_Weekday_mon.stateChanged.connect(callback)
        callback = self._on_checkBox_ShowItem_stateChanged
        ui.checkBox_Weekday_tue.stateChanged.connect(callback)
        callback = self._on_checkBox_ShowItem_stateChanged
        ui.checkBox_Weekday_wed.stateChanged.connect(callback)
        callback = self._on_checkBox_ShowItem_stateChanged
        ui.checkBox_Weekday_thu.stateChanged.connect(callback)
        callback = self._on_checkBox_ShowItem_stateChanged
        ui.checkBox_Weekday_fri.stateChanged.connect(callback)

        row_cnt = ui.tableWidget.rowCount()
        for i in reversed(range(row_cnt)):
            ui.tableWidget.removeRow(i)

        col_cnt = ui.tableWidget.columnCount()
        header = ui.tableWidget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        for i in range(col_cnt - 1):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        vHeaderView = ui.tableWidget.verticalHeader()
        hHeaderView = ui.tableWidget.horizontalHeader()
        vHeaderView.setDefaultSectionSize(100)

        callback = self._on_vHeaderView_sectionResized
        vHeaderView.sectionResized.connect(callback)
        callback = self._on_hHeaderView_sectionResized
        hHeaderView.sectionResized.connect(callback)

        self._CHECKSTATE_WEEKDAY_DICT = {
            WEEKDAY_ID_MON: ui.checkBox_Weekday_mon.checkState,
            WEEKDAY_ID_TUE: ui.checkBox_Weekday_tue.checkState,
            WEEKDAY_ID_WED: ui.checkBox_Weekday_wed.checkState,
            WEEKDAY_ID_THU: ui.checkBox_Weekday_thu.checkState,
            WEEKDAY_ID_FRI: ui.checkBox_Weekday_fri.checkState
        }

        self._CHECKSTATE_GOTODAY_DICT = {
            self._GOTODAY_ID_T: ui.checkBox_GotoDay_true.checkState,
            self._GOTODAY_ID_F: ui.checkBox_GotoDay_false.checkState,
        }

        self._CHECKSTATE_CHARTTYP_DICT = {
            self._CHART_TYP_STATISTICS: ui.checkBox_ChartTyp_stat.checkState,
            self._CHART_TYP_CUMSUM: ui.checkBox_ChartTyp_cumsum.checkState,
        }

        self._drm = DateRangeManager()
        self._logger = utl.get_logger()
        self._ui = ui
        self._df_base = pd.DataFrame()
        self._df_wg = pd.DataFrame()
        self._gran_id = None
        self._decimal_digit = None
        self._chart_idx_list = []
        self._is_require_reconstruct_table = True

    def set_data(self, df_base, gran_id, decimal_digit):

        date_list = list(df_base.groupby(COL_DATE).groups.keys())

        self._drm.init_date_list(date_list)

        qdate_l = QDate.fromString(self._drm.lower_date, FMT_QT_DATE_YMD)
        qdate_u = QDate.fromString(self._drm.upper_date, FMT_QT_DATE_YMD)

        self._df_base = df_base
        self._df_wg = ttmcom.convert_base2weekgoto(df_base)
        self._gran_id = gran_id
        self._decimal_digit = decimal_digit

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
        self._logger.debug("--- on_tableWidget_rowResized ----------")

        vHeaderView = self._ui.tableWidget.verticalHeader()
        vHeaderView.setDefaultSectionSize(newSize)

    def _on_hHeaderView_sectionResized(self, index, oldSize, newSize):
        self._logger.debug("--- on_tableWidget_columnResized ----------")

    def _on_pushButton_update_clicked(self, checked):
        self._update_table()

    def _on_checkBox_autoupdate_stateChanged(self, state):
        self._logger.debug("---on_checkBox_autoupdate_stateChanged ----------")
        # self._logger.debug("state:{}".format(state))

        if state == Qt.Checked:
            self._ui.pushButton_update.setEnabled(False)
        else:
            self._ui.pushButton_update.setEnabled(True)

    def _on_lower_date_changed(self, qdate):
        self._logger.debug("---[1]on_start_date_changed ----------")

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
        self._logger.debug("---[2]on_end_date_changed ----------")

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
        self._logger.debug("---[3]on_spinBox_step_value_changed ----------")

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
        self._logger.debug("---[4]on_ScrollBar_DateRange_value_changed ----------")

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
        self._logger.debug("--- on_checkBox_ShowItem_stateChanged ----------")

        self._is_require_reconstruct_table = True

        stat = self._ui.checkBox_AutoUpdate.checkState()
        if stat == Qt.Checked:
            self._update_table()

    def _update_table(self):

        df_wg = self._get_latest_dataframe()

        if self._is_require_reconstruct_table:
            self._reconstruct_table()

        self._update_chart(df_wg)

    def _get_latest_dataframe(self):
        self._logger.debug("---[99]update_dataframe ----------")

        sdt_str = self._drm.lower_date
        sdt_end = self._drm.upper_date
        mst_list = self._df_base.index.get_level_values(level=COL_DATE)
        df_base = self._df_base[(sdt_str <= mst_list) & (mst_list <= sdt_end)]
        df_wg = ttmcom.convert_base2weekgoto(df_base)

        return df_wg

    def _reconstruct_table(self):

        row_cnt = self._ui.tableWidget.rowCount()
        for i in reversed(range(row_cnt)):
            self._ui.tableWidget.removeRow(i)

        chart_idx_list = []
        for weekday_id in self._WEEKDAY_ID_DICT.keys():
            checkState = self._CHECKSTATE_WEEKDAY_DICT[weekday_id]
            wd_stat = checkState()
            if wd_stat != Qt.Checked:
                continue

            for gotoday_id in self._GOTO_ID_DICT.keys():
                checkState = self._CHECKSTATE_GOTODAY_DICT[gotoday_id]
                gd_stat = checkState()
                if gd_stat != Qt.Checked:
                    continue

                for charttyp_id in self._CHARTTYP_LIST:
                    checkState = self._CHECKSTATE_CHARTTYP_DICT[charttyp_id]
                    gd_stat = checkState()
                    if gd_stat != Qt.Checked:
                        continue

                    chart_idx_list.append([weekday_id, gotoday_id, charttyp_id])

        for i, chart_idx in enumerate(chart_idx_list):
            weekday_id = chart_idx[0]
            gotoday_id = chart_idx[1]
            charttyp_id = chart_idx[2]

            self._ui.tableWidget.insertRow(i)

            item_wd = QTableWidgetItem(self._WEEKDAY_ID_DICT[weekday_id])
            item_wd.setTextAlignment(Qt.AlignCenter)
            self._ui.tableWidget.setItem(i, 0, item_wd)

            item_gt = QTableWidgetItem(self._GOTO_ID_DICT[gotoday_id])
            item_gt.setTextAlignment(Qt.AlignCenter)
            self._ui.tableWidget.setItem(i, 1, item_gt)

            if charttyp_id == self._CHART_TYP_STATISTICS:
                chart = LineChartTtmStatistics()
            else:
                chart = LineChartTtmCumsum()
            self._ui.tableWidget.setCellWidget(i, 2, chart)

        self._chart_idx_list = chart_idx_list
        self._is_require_reconstruct_table = False

    def _update_chart(self, df_wg):

        mst_list = df_wg.index.get_level_values(level=COL_DATA_TYP)
        df_wg_st = df_wg[mst_list < DATA_TYP_CO_CSUM]
        df_wg_cs = df_wg[mst_list == DATA_TYP_CO_CSUM]

        max_ = df_wg_st.max().max()
        min_ = df_wg_st.min().min()
        wg_st_max = max(abs(max_), abs(min_))

        max_ = df_wg_cs.max().max()
        min_ = df_wg_cs.min().min()
        wg_cs_max = max(abs(max_), abs(min_))

        for i, chart_idx in enumerate(self._chart_idx_list):
            weekday_id = chart_idx[0]
            gotoday_id = chart_idx[1]
            charttyp_id = chart_idx[2]

            if gotoday_id == self._GOTODAY_ID_T:
                is_goto = True
            else:
                is_goto = False

            if charttyp_id == self._CHART_TYP_STATISTICS:
                df_trg = df_wg_st
                max_y = wg_st_max
            else:
                df_trg = df_wg_cs
                max_y = wg_cs_max

            idxloc = (weekday_id, is_goto)
            if idxloc in df_trg.index:
                df = df_trg.loc[idxloc]
                chart = self._ui.tableWidget.cellWidget(i, 2)
                chart.set_max_y(max_y)
                chart.set_min_y(-max_y)
                chart.update(df, self._gran_id, self._decimal_digit)
            else:
                pass

    def _load_ui(self, parent):
        loader = QUiLoader()
        path = os.path.join(os.path.dirname(__file__), "ttm_details.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        ui = loader.load(ui_file, parent)
        ui_file.close()

        return ui

    def init_resize(self):
        pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
