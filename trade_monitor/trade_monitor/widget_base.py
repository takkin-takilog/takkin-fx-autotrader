from enum import Enum
import pandas as pd
from PySide2.QtWidgets import QGraphicsItem
from PySide2.QtWidgets import QWidget
from PySide2.QtWidgets import QStyleOptionGraphicsItem
from PySide2.QtWidgets import QGraphicsLineItem
from PySide2.QtWidgets import QAction, QMenu
from PySide2.QtWidgets import QTreeView
from PySide2.QtWidgets import QHeaderView
from PySide2.QtWidgets import QGridLayout
from PySide2.QtWidgets import QAbstractItemView
from PySide2.QtCharts import QtCharts
from PySide2.QtCore import QAbstractTableModel, QSortFilterProxyModel
from PySide2.QtCore import Qt, QPointF, QRectF, QRect, QLineF
from PySide2.QtCore import QDateTime, QDate, QTime, QRegExp, QModelIndex
from PySide2.QtCore import QSignalMapper, QPoint
from PySide2.QtGui import QPalette, QColor, QFont, QFontMetrics, QPainter, QPainterPath
from PySide2.QtGui import QLinearGradient, QPen
from trade_monitor.constant import GRAN_FREQ_DICT

CALLOUT_PRICE_COLOR = QColor(204, 0, 51)
CALLOUT_DATE_COLOR = QColor(0, 204, 51)


class PandasModel(QAbstractTableModel):

    def __init__(self, df=pd.DataFrame(), parent=None):
        super().__init__(parent)

        if df.index.names[0] is None:
            self._df_index_names = None
            is_drop = True
        else:
            self._df_index_names = df.index.names
            is_drop = False

        self._df_column_names = df.columns.tolist()
        self._df = df.reset_index(drop=is_drop)
        self._bolds = dict()
        self._colors = dict()

    @property
    def df_index_names(self):
        return self._df_index_names

    @property
    def df_column_names(self):
        return self._df_column_names

    def getDataFrameColumnsName(self):
        return list(self._df.columns)

    def toDataFrame(self):
        if self._df_index_names is None:
            df = self._df
        else:
            df = self._df.set_index(self._df_index_names)

        return df

    def getColumnUnique(self, column_index):
        return self._df.iloc[:, column_index].unique()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                try:
                    return self._df.columns.tolist()[section]
                except (IndexError,):
                    return None
            elif role == Qt.FontRole:
                return self._bolds.get(section, None)

            elif role == Qt.ForegroundRole:
                return self._colors.get(section, None)

        elif orientation == Qt.Vertical:
            if role == Qt.DisplayRole:
                try:
                    return self._df.index.tolist()[section]
                except (IndexError,):
                    return None
        return None

    def setFiltered(self, section, isFiltered):
        font = QFont()
        color = QColor()
        if isFiltered:
            font.setBold(True)
            color.setBlue(255)
        self._bolds[section] = font
        self._colors[section] = color
        self.headerDataChanged.emit(Qt.Horizontal, 0, self.columnCount())

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if not index.isValid():
                return None
            return str(self._df.iloc[index.row(), index.column()])

        elif role == Qt.UserRole:
            if not index.isValid():
                return None
            return self._df.iloc[index.row(), index.column()]
        else:
            return None

    def setData(self, index, value, role):
        row = self._df.index[index.row()]
        col = self._df.columns[index.column()]
        dtype = self._df[col].dtype
        if dtype != object:
            value = None if value == '' else dtype.type(value)
        self._df.set_value(row, col, value)
        return True

    def rowCount(self, parent=QModelIndex()):
        return len(self._df.index)

    def columnCount(self, parent=QModelIndex()):
        return len(self._df.columns)

    def sort(self, column, order):
        colname = self._df.columns.tolist()[column]
        self.layoutAboutToBeChanged.emit()
        self._df.sort_values(colname, ascending=order == Qt.AscendingOrder, inplace=True)
        self._df.reset_index(inplace=True, drop=True)
        self.layoutChanged.emit()

    def sortColumn(self, column, ascending):
        colname = self._df.columns.tolist()[column]
        self.layoutAboutToBeChanged.emit()
        self._df.sort_values(colname, ascending=ascending, inplace=True)
        self._df.reset_index(inplace=True, drop=True)
        self.layoutChanged.emit()


class CustomProxyModel(QSortFilterProxyModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filters = dict()

    @property
    def filters(self):
        return self._filters

    def setFilter(self, expresion, column):
        if expresion:
            self.filters[column] = expresion
        elif column in self.filters:
            del self.filters[column]
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        for column, expresion in self.filters.items():
            text = self.sourceModel().index(source_row, column, source_parent).data()
            regex = QRegExp(
                expresion, Qt.CaseInsensitive, QRegExp.RegExp
            )
            if regex.indexIn(text) == -1:
                return False
        return True


class PandasTreeView(QTreeView):

    def __init__(self, parent=None):
        super().__init__(parent)

        if parent is not None:
            lay = QGridLayout(parent)
            lay.setMargin(0)
            lay.addWidget(self, 0, 0, 1, 1)

        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerItem)

        header = self.header()
        header.setSectionsClickable(True)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)

        model = PandasModel()
        proxy = CustomProxyModel()
        proxy.setSourceModel(model)
        self.setModel(proxy)

    @property
    def pandas_model(self):
        return self.model().sourceModel()

    @property
    def proxy(self):
        return self.model()

    def set_dataframe(self, df: pd.DataFrame):
        model = PandasModel(df)
        proxy = CustomProxyModel()
        proxy.setSourceModel(model)
        self.setModel(proxy)

    def show_header_menu(self, logical_index):

        self._logical_index = logical_index
        self._menu = QMenu()
        self._menu.setStyleSheet("QMenu { menu-scrollable: 1; }")
        self._signal_mapper = QSignalMapper()

        # valuesUnique = model._df.iloc[:, self._logical_index].unique()
        valuesUnique = self.pandas_model.getColumnUnique(self._logical_index)

        actAll = QAction("All", self)
        actAll.triggered.connect(self._on_actionAll_triggered)
        self._menu.addAction(actAll)
        self._menu.addSeparator()

        actOrderAsc = QAction("Order Asc", self)
        actOrderAsc.triggered.connect(self._on_actionOrderAsc_triggered)
        self._menu.addAction(actOrderAsc)
        actOrderDes = QAction("Order Des", self)
        actOrderDes.triggered.connect(self._on_actionOrderDes_triggered)
        self._menu.addAction(actOrderDes)
        self._menu.addSeparator()

        for act_no, act_name in enumerate(sorted(list(set(valuesUnique)))):
            action = QAction(str(act_name), self)
            self._signal_mapper.setMapping(action, act_no)
            action.triggered.connect(self._signal_mapper.map)
            self._menu.addAction(action)
        self._signal_mapper.mapped.connect(self._on_signalMapper_mapped)

        header = self.header()
        headerPos = self.mapToGlobal(header.pos())
        posY = headerPos.y() + header.height()
        posX = headerPos.x() + header.sectionPosition(self._logical_index)

        self._menu.exec_(QPoint(posX, posY))

    def is_selected(self):
        if self.selectionModel().selectedRows():
            flag = True
        else:
            flag = False
        return flag

    def get_dataframe(self, is_selected=False):

        if is_selected:
            df = self._get_selected_dataframe()
        else:
            df = self._get_all_dataframe()

        return df

    def _get_selected_dataframe(self):
        model_index_list = self.selectionModel().selectedRows()
        col_cnt = self.proxy.columnCount()
        tbl = []
        for model_index in model_index_list:
            r = model_index.row()
            rec = []
            for c in range(col_cnt):
                model = self.proxy.index(r, c, model_index)
                data = model.data(role=Qt.UserRole)
                rec.append(data)
            tbl.append(rec)

        df = self._convert_dataframe(tbl)
        return df

    def _get_all_dataframe(self):
        row_cnt = self.proxy.rowCount()
        col_cnt = self.proxy.columnCount()
        tbl = []
        for row in range(row_cnt):
            rec = []
            for col in range(col_cnt):
                modelIndex = self.proxy.index(row, col)
                data = modelIndex.data(role=Qt.UserRole)
                rec.append(data)
            tbl.append(rec)

        df = self._convert_dataframe(tbl)
        return df

    def _convert_dataframe(self, table):

        index_names = self.pandas_model.df_index_names
        column_names = self.pandas_model.df_column_names

        if index_names:
            labels = index_names + column_names
            df = pd.DataFrame(table,
                              columns=labels)
            df.set_index(index_names, inplace=True)
        else:
            df = pd.DataFrame(table,
                              columns=column_names)

        return df

    def _on_actionAll_triggered(self):
        filterColumn = self._logical_index
        self.proxy.setFilter("", filterColumn)
        self.pandas_model.setFiltered(filterColumn, False)

    def _on_actionOrderAsc_triggered(self):
        orderColumn = self._logical_index
        self.pandas_model.sortColumn(orderColumn, True)

    def _on_actionOrderDes_triggered(self):
        orderColumn = self._logical_index
        self.pandas_model.sortColumn(orderColumn, False)

    def _on_signalMapper_mapped(self, i):
        stringAction = self._signal_mapper.mapping(i).text()
        filterColumn = self._logical_index
        self.proxy.setFilter(stringAction, filterColumn)
        self.pandas_model.setFiltered(filterColumn, True)


class BaseCalloutChart(QGraphicsItem):

    def __init__(self, parent: QtCharts.QChart):
        super().__init__()
        self._chart = parent
        self._text = ""
        self._anchor = QPointF()
        self._font = QFont()
        self._textRect = QRectF()
        self._rect = QRectF()
        self._backgroundColor = QColor(Qt.black)
        self._textColor = QColor(Qt.white)

    def updateGeometry(self, text: str, point: QPointF):
        raise NotImplementedError()

    def boundingRect(self) -> QRectF:
        # print("--- boundingRect ---")
        from_parent = self.mapFromParent(self._anchor)
        anchor = QPointF(from_parent)
        rect = QRectF()
        rect.setLeft(min(self._rect.left(), anchor.x()))
        rect.setRight(max(self._rect.right(), anchor.x()))
        rect.setTop(min(self._rect.top(), anchor.y()))
        rect.setBottom(max(self._rect.bottom(), anchor.y()))
        return rect

    def paint(self,
              painter: QPainter,
              option: QStyleOptionGraphicsItem,
              widget: QWidget):
        raise NotImplementedError()

    def setBackgroundColor(self, color: QColor):
        self._backgroundColor = color

    def setTextColor(self, color: QColor):
        self._textColor = color

    def _setText(self, text: str):
        self._text = text

        metrics = QFontMetrics(self._chart.font())
        self._textRect = QRectF(metrics.boundingRect(QRect(0, 0, 0, 0),
                                                     Qt.AlignLeft,
                                                     self._text))
        dx = 5
        dy = 5
        self._textRect.translate(dx, dy)
        self.prepareGeometryChange()
        self._rect = self._textRect.adjusted(-dx, -dy, dx, dy)


class CalloutDataTime(BaseCalloutChart):

    def __init__(self, parent: QtCharts.QChart):
        super().__init__(parent)

    def updateGeometry(self, text: str, point: QPointF):

        self._setText(text)
        self._anchor = point

        self.prepareGeometryChange()
        anchor = QPointF()
        anchor.setX(self._anchor.x() - self._rect.width() / 2)
        anchor.setY(self._chart.plotArea().bottom())
        self.setPos(anchor)

    def paint(self,
              painter: QPainter,
              option: QStyleOptionGraphicsItem,
              widget: QWidget):
        path = QPainterPath()
        path.addRoundedRect(self._rect, 5, 5)   # 丸みを帯びた長方形の角を規定

        # 枠を描写
        painter.setBrush(self._backgroundColor)    # 図形の塗りつぶし
        painter.setPen(QPen(self._backgroundColor))
        painter.drawPath(path)

        # 文字を描写
        painter.setPen(QPen(self._textColor))
        painter.drawText(self._textRect, self._text)


class CallouPrice(BaseCalloutChart):

    def __init__(self, parent: QtCharts.QChart):
        super().__init__(parent)

    def updateGeometry(self, text: str, point: QPointF):

        self._setText(text)
        self._anchor = point

        self.prepareGeometryChange()
        anchor = QPointF()
        anchor.setX(self._chart.plotArea().left() - self._rect.width())
        anchor.setY(self._anchor.y() - self._rect.height() / 2)
        self.setPos(anchor)

    def paint(self,
              painter: QPainter,
              option: QStyleOptionGraphicsItem,
              widget: QWidget):
        path = QPainterPath()
        path.addRoundedRect(self._rect, 5, 5)   # 丸みを帯びた長方形の角を規定

        # 枠を描写
        painter.setBrush(self._backgroundColor)    # 図形の塗りつぶし
        painter.setPen(QPen(self._backgroundColor))
        painter.drawPath(path)

        # 文字を描写
        painter.setPen(QPen(self._textColor))
        painter.drawText(self._textRect, self._text)


class BaseCandlestickChartView(QtCharts.QChartView):

    class CandleLabel(Enum):
        """
        Candlestick data label.
        """
        OP = "open"
        HI = "high"
        LO = "low"
        CL = "close"

        @classmethod
        def to_list(cls):
            return [m.value for m in cls]

    def __init__(self, parent=None):
        super().__init__(parent)

        self._CALLOUT_DT_FMT = "yyyy/MM/dd hh:mm"

        if parent is not None:
            lay = QGridLayout(parent)
            lay.setMargin(0)
            lay.addWidget(self, 0, 0, 1, 1)

        # ---------- Create Chart ----------
        chart = QtCharts.QChart()
        chart.layout().setContentsMargins(0, 0, 0, 0)
        chart.setBackgroundRoundness(0)

        # ---------- Add Series on chart ----------
        ser_cdl = QtCharts.QCandlestickSeries()
        ser_cdl.setDecreasingColor(Qt.red)
        ser_cdl.setIncreasingColor(Qt.green)
        chart.addSeries(ser_cdl)

        """
        # ---------- Set font on chart ----------
        font = QFont("Sans Serif", )
        font.setPixelSize(18)
        chart.setTitleFont(font)
        """

        # ---------- Set palette on chart ----------
        palette = QPalette()
        palette.setColor(QPalette.Text, Qt.red)
        chart.setPalette(palette)

        # ---------- Set PlotAreaBackground on chart ----------
        plotAreaGradient = QLinearGradient(0, 100, 0, 400)
        plotAreaGradient.setColorAt(0.0, QColor("#f1f1f1"))
        plotAreaGradient.setColorAt(1.0, QColor("#ffffff"))
        chart.setPlotAreaBackgroundBrush(plotAreaGradient)
        chart.setPlotAreaBackgroundVisible(True)

        # ---------- Set X Axis on chart ----------
        axis_x = QtCharts.QDateTimeAxis()
        axis_x.setTickCount(2)
        axis_x.setTitleText("Date")
        axis_x.setFormat("h:mm")
        axis_x.setLabelsAngle(0)

        now = QDateTime.currentDateTime()
        yesterday = QDateTime(QDate(now.date().year(),
                                    now.date().month(),
                                    now.date().day() - 1),
                              QTime(0, 0))
        today = QDateTime(QDate(now.date().year(),
                                now.date().month(),
                                now.date().day()),
                          QTime(0, 0))
        axis_x.setRange(yesterday, today)
        chart.addAxis(axis_x, Qt.AlignBottom)
        ser_cdl.attachAxis(axis_x)

        # ---------- Set Y Axis on chart ----------
        axis_y = QtCharts.QValueAxis()
        chart.addAxis(axis_y, Qt.AlignLeft)
        ser_cdl.attachAxis(axis_y)

        # ---------- Set Animation on chart ----------
        chart.setAnimationOptions(QtCharts.QChart.SeriesAnimations)

        # ---------- Set Legend on chart ----------
        chart.legend().hide()
        chart.legend().setVisible(False)

        self.setChart(chart)

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

        self._ser_cdl = ser_cdl
        self._decimal_digit = 0
        self._freq = "D"

    def set_max_y(self, max_y):
        self._max_y = max_y

    def set_min_y(self, min_y):
        self._min_y = min_y

    def update(self, df, gran_id, decimal_digit):

        self._ser_cdl.clear()
        for dt_, sr in df.iterrows():
            op = sr[self.CandleLabel.OP.value]
            hi = sr[self.CandleLabel.HI.value]
            lo = sr[self.CandleLabel.LO.value]
            cl = sr[self.CandleLabel.CL.value]
            qd = QDate(dt_.year, dt_.month, dt_.day)
            qt = QTime(dt_.hour, dt_.minute)
            qdt = QDateTime(qd, qt)
            cnd = QtCharts.QCandlestickSet(op, hi, lo, cl,
                                           qdt.toMSecsSinceEpoch())
            self._ser_cdl.append(cnd)

        chart = self.chart()
        chart.axisY().setRange(self._min_y, self._max_y)

        self._decimal_digit = decimal_digit
        self._freq = GRAN_FREQ_DICT[gran_id]

    def get_candle_labels_list(self):
        return self.CandleLabel.to_list()

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

        chart = self.chart()
        flag = chart.plotArea().contains(event.pos())
        if flag:
            m2v = chart.mapToValue(event.pos())
            pdt = QDateTime.fromMSecsSinceEpoch(round(m2v.x())).toPython()
            pdt = pd.to_datetime(pdt).round(self._freq)

            qd = QDate(pdt.year, pdt.month, pdt.day)
            qt = QTime(pdt.hour, pdt.minute, pdt.second)
            qdttm = QDateTime(qd, qt)

            m2v.setX(qdttm.toMSecsSinceEpoch())
            m2p = chart.mapToPosition(m2v)
            dtstr = qdttm.toString(self._CALLOUT_DT_FMT)
            self._callout_dt.updateGeometry(dtstr, m2p)
            self._callout_dt.show()

            fmt = "{:." + str(self._decimal_digit) + "f}"
            prstr = fmt.format(m2v.y())
            self._callout_pr.updateGeometry(prstr, event.pos())
            self._callout_pr.show()

            plotAreaRect = chart.plotArea()
            self._callout_vl.setLine(QLineF(m2p.x(),
                                            plotAreaRect.top(),
                                            m2p.x(),
                                            plotAreaRect.bottom()))
            self._callout_vl.show()

            self._callout_hl.setLine(QLineF(plotAreaRect.left(),
                                            event.pos().y(),
                                            plotAreaRect.right(),
                                            event.pos().y()))
            self._callout_hl.show()

        else:
            self._callout_dt.hide()
            self._callout_pr.hide()
            self._callout_vl.hide()
            self._callout_hl.hide()


class BaseLineChartView(QtCharts.QChartView):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._CALLOUT_DT_FMT = "yyyy/MM/dd hh:mm"

        if parent is not None:
            lay = QGridLayout(parent)
            lay.setMargin(0)
            lay.addWidget(self, 0, 0, 1, 1)

        # ---------- Create Chart ----------
        chart = QtCharts.QChart()
        chart.setBackgroundBrush(Qt.red)
        chart.layout().setContentsMargins(0, 0, 0, 0)
        chart.setBackgroundRoundness(0)

        """
        # ---------- Set font on chart ----------
        font = QFont("Sans Serif", )
        font.setPixelSize(18)
        chart.setTitleFont(font)
        """

        # ---------- Set palette on chart ----------
        """
        palette = QPalette()
        palette.setColor(QPalette.Text, Qt.red)
        chart.setPalette(palette)
        """

        # ---------- Set PlotAreaBackground on chart ----------
        plotAreaGradient = QLinearGradient(0, 100, 0, 400)
        plotAreaGradient.setColorAt(0.0, QColor("#f1f1f1"))
        plotAreaGradient.setColorAt(1.0, QColor("#ffffff"))
        chart.setPlotAreaBackgroundBrush(plotAreaGradient)
        chart.setPlotAreaBackgroundVisible(True)

        # ---------- Set X Axis on chart ----------
        axis_x = QtCharts.QDateTimeAxis()
        axis_x.setTickCount(2)
        # axis_x.setTitleText("Date")
        axis_x.setFormat("h:mm")
        axis_x.setLabelsAngle(0)

        now = QDateTime.currentDateTime()
        yesterday = QDateTime(QDate(now.date().year(),
                                    now.date().month(),
                                    now.date().day() - 1),
                              QTime(0, 0))
        today = QDateTime(QDate(now.date().year(),
                                now.date().month(),
                                now.date().day()),
                          QTime(0, 0))
        axis_x.setRange(yesterday, today)
        chart.addAxis(axis_x, Qt.AlignBottom)

        # ---------- Set Y Axis on chart ----------
        axis_y = QtCharts.QValueAxis()
        chart.addAxis(axis_y, Qt.AlignLeft)

        # ---------- Set Animation on chart ----------
        # chart.setAnimationOptions(QtCharts.QChart.SeriesAnimations)

        # ---------- Set Legend on chart ----------
        chart.legend().hide()
        chart.legend().setVisible(False)

        self.setChart(chart)

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

        self._decimal_digit = 0
        self._freq = "D"

    def set_max_y(self, max_y):
        self._max_y = max_y

    def set_min_y(self, min_y):
        self._min_y = min_y

    def update(self, gran_id, decimal_digit):

        chart = self.chart()
        chart.axisY().setRange(self._min_y, self._max_y)

        self._decimal_digit = decimal_digit
        self._freq = GRAN_FREQ_DICT[gran_id]

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

        chart = self.chart()
        flag = chart.plotArea().contains(event.pos())
        if flag:
            m2v = chart.mapToValue(event.pos())
            pdt = QDateTime.fromMSecsSinceEpoch(round(m2v.x())).toPython()
            pdt = pd.to_datetime(pdt).round(self._freq)

            qd = QDate(pdt.year, pdt.month, pdt.day)
            qt = QTime(pdt.hour, pdt.minute, pdt.second)
            qdttm = QDateTime(qd, qt)

            m2v.setX(qdttm.toMSecsSinceEpoch())
            m2p = chart.mapToPosition(m2v)
            dtstr = qdttm.toString(self._CALLOUT_DT_FMT)
            self._callout_dt.updateGeometry(dtstr, m2p)
            self._callout_dt.show()

            fmt = "{:." + str(self._decimal_digit) + "f}"
            prstr = fmt.format(m2v.y())
            self._callout_pr.updateGeometry(prstr, event.pos())
            self._callout_pr.show()

            plotAreaRect = chart.plotArea()
            self._callout_vl.setLine(QLineF(m2p.x(),
                                            plotAreaRect.top(),
                                            m2p.x(),
                                            plotAreaRect.bottom()))
            self._callout_vl.show()

            self._callout_hl.setLine(QLineF(plotAreaRect.left(),
                                            event.pos().y(),
                                            plotAreaRect.right(),
                                            event.pos().y()))
            self._callout_hl.show()

        else:
            self._callout_dt.hide()
            self._callout_pr.hide()
            self._callout_vl.hide()
            self._callout_hl.hide()