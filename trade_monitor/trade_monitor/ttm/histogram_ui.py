import os
from enum import Enum
import pandas as pd
from PySide2.QtCore import QPointF, QLineF, QFile, Qt
from PySide2.QtGui import QColor, QPen
from PySide2.QtGui import QLinearGradient, QGradient
from PySide2.QtWidgets import QMainWindow
from PySide2.QtWidgets import QGraphicsLineItem
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCharts import QtCharts
from trade_monitor.widget_base import PandasTreeView
from trade_monitor.widget_base import BaseView
from trade_monitor.widget_base import CallouPrice, CalloutDataTime
from trade_monitor.widget_base import CALLOUT_PRICE_COLOR, CALLOUT_DATE_COLOR
from trade_monitor.constant import InstParam
from trade_monitor import utility as utl


class ColumnName(Enum):
    DATE = "date"
    PRICE_HIOP = "high-open price"
    PRICE_LOOP = "low-open price"
    PRICE_CLOP = "close-open price"

    @classmethod
    def to_list(cls):
        return [m.value for m in cls]


class BaseHistogramView(BaseView):

    _CALLOUT_PRICE_COLOR = QColor(204, 0, 51)

    def __init__(self, parent=None):
        super().__init__(parent)

        chart = self.chart()

        # ---------- Set X Axis on chart ----------
        axis_x = QtCharts.QValueAxis()
        axis_x.setTitleText("Count")
        axis_x.setLabelFormat("%d")
        chart.addAxis(axis_x, Qt.AlignBottom)

        # ---------- Set Y Axis on chart ----------
        axis_y = QtCharts.QValueAxis()
        axis_y.setTitleText("Price")
        chart.addAxis(axis_y, Qt.AlignLeft)

        # ---------- Add Horizon Zero Line on scene ----------
        self._hl_zero = QGraphicsLineItem()
        pen = self._hl_zero.pen()
        pen.setColor(QColor(Qt.black))
        pen.setWidth(1)
        pen.setStyle(Qt.DashLine)
        self._hl_zero.setPen(pen)
        self._hl_zero.setZValue(1)
        self.scene().addItem(self._hl_zero)

        # ---------- Add CallouPrice on scene ----------
        self._callout_pr = CallouPrice(chart)
        self._callout_pr.setBackgroundColor(self._CALLOUT_PRICE_COLOR)
        self._callout_pr.setZValue(100)
        self.scene().addItem(self._callout_pr)

        # ---------- Add CallouHorizontalLine on scene ----------
        self._callout_hl = QGraphicsLineItem()
        pen = self._callout_hl.pen()
        pen.setColor(self._CALLOUT_PRICE_COLOR)
        pen.setWidth(1)
        self._callout_hl.setPen(pen)
        self._callout_hl.setZValue(100)
        self.scene().addItem(self._callout_hl)

        self._axis_x = axis_x
        self._axis_y = axis_y
        self._bar_color = Qt.white
        self._pen_color = Qt.black
        self._is_update = False
        self._inst_param = InstParam.USDJPY

    def set_pen_color(self, color: QColor):
        self._pen_color = color

    def set_bar_color(self, color: QColor):
        self._bar_color = color

    def update(self, sr_hist: pd.Series, inst_param: InstParam):
        super().update()

        chart = self.chart()

        chart.removeAllSeries()
        self._LineSeriesList = []
        self._axis_x.setTickCount(self._max_x + 1)

        ofs = inst_param.lsb_value / 2
        print(ofs)
        for idx in sr_hist.index:
            series_u = QtCharts.QLineSeries()
            series_u.append(QPointF(0, idx + ofs))
            series_u.append(QPointF(sr_hist[idx], idx + ofs))
            series_l = QtCharts.QLineSeries()
            series_l.append(QPointF(0, idx - ofs))
            series_l.append(QPointF(sr_hist[idx], idx - ofs))
            series = QtCharts.QAreaSeries(series_u, series_l)
            pen = series.pen()
            pen.setWidth(1)
            # pen.setStyle(Qt.NoPen)
            pen.setColor(self._pen_color)
            series.setPen(pen)
            chart.addSeries(series)
            self._LineSeriesList.append(series_u)
            self._LineSeriesList.append(series_l)
            series.setColor(self._bar_color)
            series.attachAxis(self._axis_x)
            series.attachAxis(self._axis_y)

        self._is_update = True
        self._inst_param = inst_param

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if self._is_update:
            self._update_callout()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

        chart = self.chart()
        flag = chart.plotArea().contains(event.pos())
        if flag:
            m2v = chart.mapToValue(event.pos())
            xpos = utl.roundi(m2v.x())
            ypos = utl.roundf(m2v.y(), digit=self._inst_param.digit)
            new_pos = QPointF(xpos, ypos)
            m2p = chart.mapToPosition(new_pos)

            fmt = "{:." + str(self._inst_param.digit) + "f}"
            prstr = fmt.format(new_pos.y())
            self._callout_pr.updateGeometry(prstr, m2p)
            self._callout_pr.show()

            plotAreaRect = chart.plotArea()
            self._callout_hl.setLine(QLineF(plotAreaRect.left(),
                                            m2p.y(),
                                            plotAreaRect.right(),
                                            m2p.y()))
            self._callout_hl.show()
        else:
            self._callout_pr.hide()
            self._callout_hl.hide()

    def _update_callout(self):

        chart = self.chart()

        # drow Horizontal Zreo Line
        zero_point = QPointF(0, 0)
        m2p = chart.mapToPosition(zero_point)
        plotAreaRect = chart.plotArea()
        self._hl_zero.setLine(QLineF(plotAreaRect.left(),
                                     m2p.y(),
                                     plotAreaRect.right(),
                                     m2p.y()))
        self._hl_zero.show()


class HistogramViewHigh(BaseHistogramView):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chart().setTitle("High - Open Price")

        self.set_pen_color(Qt.darkMagenta)
        self.set_bar_color(Qt.magenta)


class HistogramViewClose(BaseHistogramView):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chart().setTitle("Close - Open Price")

        self.set_pen_color(Qt.darkGreen)
        self.set_bar_color(Qt.green)


class HistogramViewLow(BaseHistogramView):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chart().setTitle("Low - Open Price")

        self.set_pen_color(Qt.darkCyan)
        self.set_bar_color(Qt.cyan)


class ChartView(BaseView):

    def __init__(self, parent=None):
        super().__init__(parent)

        # self.setRubberBand(QtCharts.QChartView.HorizontalRubberBand)

        chart = self.chart()
        chart.setTitle("Date Lines chart")

        # ---------- Add Series on chart ----------
        series_hi = QtCharts.QAreaSeries()
        pen = QPen(Qt.darkMagenta)
        pen.setWidth(1)
        series_hi.setPen(pen)
        series_hi.setBrush(Qt.magenta)
        chart.addSeries(series_hi)

        series_lo = QtCharts.QAreaSeries()
        pen = QPen(Qt.darkCyan)
        pen.setWidth(1)
        series_lo.setPen(pen)
        series_lo.setBrush(Qt.cyan)
        chart.addSeries(series_lo)

        series_cl = QtCharts.QAreaSeries()
        pen = QPen(Qt.darkGreen)
        pen.setWidth(1)
        series_cl.setPen(pen)
        series_cl.setBrush(Qt.green)
        chart.addSeries(series_cl)

        # ---------- Set X Axis on chart ----------
        axis_x = QtCharts.QBarCategoryAxis()
        axis_x.setTitleText("Date")
        axis_x.setLabelsAngle(0)
        axis_x.setLabelsVisible(False)
        axis_x.setMinorGridLineVisible(False)
        axis_x.setLineVisible(False)
        axis_x.setGridLineVisible(False)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series_hi.attachAxis(axis_x)
        series_lo.attachAxis(axis_x)
        series_cl.attachAxis(axis_x)

        # ---------- Set Y Axis on chart ----------
        axis_y = QtCharts.QValueAxis()
        axis_y.setTitleText("Price")
        chart.addAxis(axis_y, Qt.AlignLeft)
        series_hi.attachAxis(axis_y)
        series_lo.attachAxis(axis_y)
        series_cl.attachAxis(axis_y)

        # ---------- Add Horizon Zero Line on scene ----------
        self._hl_zero = QGraphicsLineItem()
        pen = self._hl_zero.pen()
        pen.setColor(QColor(Qt.black))
        pen.setWidth(1)
        pen.setStyle(Qt.DashLine)
        self._hl_zero.setPen(pen)
        self._hl_zero.setZValue(1)
        self.scene().addItem(self._hl_zero)

        # ---------- Add CalloutDataTime on scene ----------
        self._callout_dt = CalloutDataTime(chart)
        self._callout_dt.setBackgroundColor(CALLOUT_DATE_COLOR)
        self._callout_dt.setZValue(100)
        self.scene().addItem(self._callout_dt)

        # ---------- Add CallouPrice on scene ----------
        self._callout_pr = CallouPrice(chart)
        self._callout_pr.setBackgroundColor(CALLOUT_PRICE_COLOR)
        self._callout_pr.setZValue(100)
        self.scene().addItem(self._callout_pr)

        # ---------- Add CallouVerticalLine on scene ----------
        self._callout_vl = QGraphicsLineItem()
        pen = self._callout_vl.pen()
        pen.setColor(CALLOUT_DATE_COLOR)
        pen.setWidth(1)
        self._callout_vl.setPen(pen)
        self._callout_vl.setZValue(100)
        self.scene().addItem(self._callout_vl)

        # ---------- Add CallouHorizontalLine on scene ----------
        self._callout_hl = QGraphicsLineItem()
        pen = self._callout_hl.pen()
        pen.setColor(CALLOUT_PRICE_COLOR)
        pen.setWidth(1)
        self._callout_hl.setPen(pen)
        self._callout_hl.setZValue(100)
        self.scene().addItem(self._callout_hl)

        self._series_hi = series_hi
        self._series_lo = series_lo
        self._series_cl = series_cl
        self._is_update = False
        self._inst_param = InstParam.USDJPY

    def update(self, df: pd.DataFrame, inst_param: InstParam):
        super().update()

        self._lineser_u_hi = QtCharts.QLineSeries()
        self._lineser_u_lo = QtCharts.QLineSeries()
        self._lineser_u_cl = QtCharts.QLineSeries()
        self._lineser_l = QtCharts.QLineSeries()

        for i, (_, row) in enumerate(df.iterrows()):
            self._lineser_u_hi.append(QPointF(i, row[ColumnName.PRICE_HIOP.value]))
            self._lineser_u_lo.append(QPointF(i, row[ColumnName.PRICE_LOOP.value]))
            self._lineser_u_cl.append(QPointF(i, row[ColumnName.PRICE_CLOP.value]))
            self._lineser_l.append(QPointF(i, 0))

        self._series_hi.setUpperSeries(self._lineser_u_hi)
        self._series_hi.setLowerSeries(self._lineser_l)
        self._series_cl.setUpperSeries(self._lineser_u_cl)
        self._series_cl.setLowerSeries(self._lineser_l)
        self._series_lo.setUpperSeries(self._lineser_u_lo)
        self._series_lo.setLowerSeries(self._lineser_l)

        self.chart().axisX().setCategories(df.index)

        self._inst_param = inst_param
        self._is_update = True

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if self._is_update:
            self._update_callout()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

        chart = self.chart()
        flag = chart.plotArea().contains(event.pos())
        if flag:
            m2v = chart.mapToValue(event.pos())
            xpos = utl.roundi(m2v.x())
            ypos = utl.roundf(m2v.y(), digit=self._inst_param.digit)
            new_pos = QPointF(xpos, ypos)
            m2p = chart.mapToPosition(new_pos)

            x_label_list = chart.axisX().categories()
            dtstr = x_label_list[xpos]
            self._callout_dt.updateGeometry(dtstr, m2p)
            self._callout_dt.show()

            fmt = "{:." + str(self._inst_param.digit) + "f}"
            prstr = fmt.format(new_pos.y())
            self._callout_pr.updateGeometry(prstr, m2p)
            self._callout_pr.show()

            plotAreaRect = chart.plotArea()
            self._callout_vl.setLine(QLineF(m2p.x(),
                                            plotAreaRect.top(),
                                            m2p.x(),
                                            plotAreaRect.bottom()))
            self._callout_vl.show()

            self._callout_hl.setLine(QLineF(plotAreaRect.left(),
                                            m2p.y(),
                                            plotAreaRect.right(),
                                            m2p.y()))
            self._callout_hl.show()
        else:
            self._callout_dt.hide()
            self._callout_pr.hide()
            self._callout_vl.hide()
            self._callout_hl.hide()

    def _update_callout(self):

        chart = self.chart()

        # drow Horizontal Zreo Line
        zero_point = QPointF(0, 0)
        m2p = chart.mapToPosition(zero_point)
        plotAreaRect = chart.plotArea()
        self._hl_zero.setLine(QLineF(plotAreaRect.left(),
                                     m2p.y(),
                                     plotAreaRect.right(),
                                     m2p.y()))
        self._hl_zero.show()


class HistogramUi(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)

        ui = self._load_ui(parent, "histogram.ui")
        self.setCentralWidget(ui)
        self.resize(ui.frameSize())
        # self.setWindowTitle("TTM Histogram")

        # set TreeView
        pdtreeview = PandasTreeView(ui.widget_TreeView)
        header = pdtreeview.header()
        callback = self._on_view_header_sectionClicked
        header.sectionClicked.connect(callback)

        # set HistogramView
        histview_hi = HistogramViewHigh(ui.widget_HistView_hi)
        histview_cl = HistogramViewClose(ui.widget_HistView_cl)
        histview_lo = HistogramViewLow(ui.widget_HistView_lo)

        # set ChartView
        chartview = ChartView(ui.widget_ChartView)

        # self._logger = ros_com.get_logger()
        self._ui = ui
        self._pdtreeview = pdtreeview
        self._histview_hi = histview_hi
        self._histview_cl = histview_cl
        self._histview_lo = histview_lo
        self._chartview = chartview

    def set_data(self, df: pd.DataFrame, inst_param: InstParam):
        print("========== df ==========")
        print(df)

        print("========== df.hist ==========")
        df_hist = df.apply(pd.value_counts)
        counts_max = df_hist.max().max() + 1
        print(df_hist)
        print("--- counts_max ---")
        print(counts_max)

        lsb = inst_param.lsb_value
        index_max = max(abs(df_hist.index[0]), abs(df_hist.index[-1])) + lsb * 3
        print("--- index_max ---")
        print(index_max)

        sr_hi = df_hist[ColumnName.PRICE_HIOP.value].fillna(0)
        sr_cl = df_hist[ColumnName.PRICE_CLOP.value].fillna(0)
        sr_lo = df_hist[ColumnName.PRICE_LOOP.value].fillna(0)

        # set TreeView
        self._pdtreeview.set_dataframe(df)

        # set ChartView
        max_val = df[ColumnName.PRICE_HIOP.value].max()
        min_val = df[ColumnName.PRICE_LOOP.value].min()

        max_y = max(abs(max_val), abs(min_val))
        min_y = -max_y

        dif = max_y * 0.05
        self._chartview.set_max_y(max_y + dif)
        self._chartview.set_min_y(min_y - dif)

        self._histview_hi.set_max_x(counts_max)
        self._histview_hi.set_min_x(0)
        self._histview_hi.set_max_y(index_max)
        self._histview_hi.set_min_y(-index_max)

        self._histview_cl.set_max_x(counts_max)
        self._histview_cl.set_min_x(0)
        self._histview_cl.set_max_y(index_max)
        self._histview_cl.set_min_y(-index_max)

        self._histview_lo.set_max_x(counts_max)
        self._histview_lo.set_min_x(0)
        self._histview_lo.set_max_y(index_max)
        self._histview_lo.set_min_y(-index_max)

        self._histview_hi.update(sr_hi, inst_param)
        self._histview_cl.update(sr_cl, inst_param)
        self._histview_lo.update(sr_lo, inst_param)
        self._chartview.update(df, inst_param)

    def _on_view_header_sectionClicked(self, logical_index):
        self._pdtreeview.show_header_menu(logical_index)

    def _load_ui(self, parent, ui_name: str):
        loader = QUiLoader()
        path = os.path.join(os.path.dirname(__file__), ui_name)
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        ui = loader.load(ui_file, parent)
        ui_file.close()

        return ui


if __name__ == "__main__":
    import sys
    from PySide2.QtCore import QCoreApplication
    from PySide2.QtWidgets import QApplication

    data = [["2020-10-12", 0.021, 0.000, 0.015],
            ["2020-10-19", 0.004, -0.021, -0.019],
            ["2020-10-26", 0.009, -0.008, -0.007],
            ["2020-11-02", 0.003, -0.012, 0.003],
            ["2020-11-09", 0.003, -0.015, -0.006],
            ["2020-11-16", 0.003, -0.014, -0.010],
            ["2020-11-23", 0.001, -0.004, -0.004],
            ["2020-12-07", 0.008, 0.000, 0.002],
            ["2020-12-14", 0.020, -0.006, 0.018],
            ["2020-12-21", 0.026, 0.000, 0.026]]
    df = pd.DataFrame(data,
                      columns=ColumnName.to_list())
    df.set_index(ColumnName.DATE.value, inplace=True)

    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication([])
    widget = HistogramUi()
    widget.setWindowTitle("Time Axis Analysis [9:10]")
    widget.set_data(df, InstParam.USDJPY)
    widget.show()
    sys.exit(app.exec_())
