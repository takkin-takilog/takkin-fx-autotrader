import pandas as pd
import datetime as dt

from PySide2.QtGui import QStandardItemModel, QStandardItem
from PySide2.QtCore import QItemSelectionModel

import rclpy

from trade_monitor.candlestick_chart import CandlestickChart

from trade_apl_msgs.srv import GapFillMntSrv
from trade_apl_msgs.msg import GapFillMsg
from trade_manager_msgs.msg import Granularity as Gran
from trade_manager_msgs.srv import CandlesMntSrv

from trade_monitor.util import INST_MSG_LIST
from trade_monitor.util import DT_FMT
from trade_monitor.util import CANDLE_COL_NAME_LIST
from trade_monitor.util import (COL_NAME_TIME,
                                COL_NAME_ASK_OP,
                                COL_NAME_ASK_HI,
                                COL_NAME_ASK_LO,
                                COL_NAME_ASK_CL
                                )


class GapFill():

    GAP_DIR_DICT = {
        GapFillMsg.GAP_DIR_UP: "Up",
        GapFillMsg.GAP_DIR_DOWN: "Down"
        }

    GAP_FILL_SUCC_DICT = {
        True: "Success",
        False: "Failure"
        }

    GAP_FILL_HEADERS = [
        "Date",
        "Gap dir",
        "Previous close price",
        "Current open price",
        "Gap range price",
        "Gap fill result",
        "Gap filled time",
        "Max open range",
        "End close price"
    ]

    def __init__(self, ui, node, cli_cdl) -> None:

        logger = node.get_logger()

        callback = self.__on_fetch_gapfill_clicked
        ui.pushButton_fetch_gapfill.clicked.connect(callback)

        tbl_mdl_gapfill = QStandardItemModel()
        self.selModel = QItemSelectionModel(tbl_mdl_gapfill)

        callback = self.__on_selection_gapfill_changed
        self.selModel.selectionChanged.connect(callback)

        # set header
        tbl_mdl_gapfill.setHorizontalHeaderLabels(self.GAP_FILL_HEADERS)
        ui.tableView_gapfill.setModel(tbl_mdl_gapfill)
        ui.treeView_gapfill.setModel(tbl_mdl_gapfill)
        ui.treeView_gapfill.setSelectionModel(self.selModel)

        csc_gapfill = CandlestickChart(ui.widget_chart_gapfill)

        # Create service client "CandlesMonitor"
        srv_type = GapFillMntSrv
        srv_name = "gapfill_monitor"
        srv_cli = node.create_client(srv_type, srv_name)
        # Wait for a service server
        while not srv_cli.wait_for_service(timeout_sec=1.0):
            logger.info("Waiting for \"" + srv_name + "\" service...")

        self.__csc_gapfill = csc_gapfill
        self.__tbl_mdl_gapfill = tbl_mdl_gapfill

        self.__inst_id = INST_MSG_LIST[0].msg_id
        self.__ui = ui

        self.__node = node
        self.__logger = logger
        self.__srv_cli = srv_cli
        self.__cli_cdl = cli_cdl
        self.__end_hour = 9

    def __on_fetch_gapfill_clicked(self):

        self.__logger.debug("gapfill start")

        self.__tbl_mdl_gapfill.clear()
        self.__tbl_mdl_gapfill.setHorizontalHeaderLabels(self.GAP_FILL_HEADERS)
        inst_idx = self.__ui.comboBox_inst_gapfill.currentIndex()
        decimal_digit = INST_MSG_LIST[inst_idx].decimal_digit
        fmt = "{:." + str(decimal_digit) + "f}"

        # fetch Gap-fill data
        req = GapFillMntSrv.Request()
        req.inst_msg.instrument_id = INST_MSG_LIST[inst_idx].msg_id

        future = self.__srv_cli.call_async(req)
        rclpy.spin_until_future_complete(self.__node, future, timeout_sec=10.0)

        flg = future.done() and future.result() is not None
        assert flg, "fetch [Gap-Fill] failed!"

        rsp = future.result()
        for gapfillmsg in rsp.gapfillmsg_list:
            items = [
                QStandardItem(gapfillmsg.date),
                QStandardItem(self.GAP_DIR_DICT[gapfillmsg.gap_dir]),
                QStandardItem(fmt.format(gapfillmsg.gap_close_price)),
                QStandardItem(fmt.format(gapfillmsg.gap_open_price)),
                QStandardItem(fmt.format(gapfillmsg.gap_range_price)),
                QStandardItem(self.GAP_FILL_SUCC_DICT[
                    gapfillmsg.is_gapfill_success]),
                QStandardItem(gapfillmsg.gap_filled_time),
                QStandardItem(fmt.format(gapfillmsg.max_open_range)),
                QStandardItem(fmt.format(gapfillmsg.end_close_price))
            ]
            self.__tbl_mdl_gapfill.appendRow(items)

        self.__end_hour = rsp.end_hour

        self.__logger.debug("gapfill end")

    def __on_selection_gapfill_changed(self, selected, deselected):

        gran_id = Gran.GRAN_M10
        inst_idx = self.__ui.comboBox_inst_gapfill.currentIndex()
        model_index = selected.at(0).indexes()[0]
        trg_date_str = self.__tbl_mdl_gapfill.item(model_index.row()).text()
        self.__logger.debug("target date: " + trg_date_str)

        trg_date = dt.datetime.strptime(trg_date_str, "%Y-%m-%d")

        dt_from = trg_date - dt.timedelta(days=2)
        dt_to = trg_date + dt.timedelta(hours=self.__end_hour)

        req = CandlesMntSrv.Request()
        req.gran_msg.granularity_id = gran_id
        req.inst_msg.instrument_id = INST_MSG_LIST[inst_idx].msg_id
        req.dt_from = dt_from.strftime(DT_FMT)
        req.dt_to = dt_to.strftime(DT_FMT)

        self.__logger.debug("dt_from: " + req.dt_from)
        self.__logger.debug("dt_to: " + req.dt_to)

        future = self.__cli_cdl.call_async(req)
        rclpy.spin_until_future_complete(self.__node, future, timeout_sec=10.0)

        flg = future.done() and future.result() is not None
        assert flg, "initial fetch [Day Candle] failed!"

        data = []
        rsp = future.result()
        for cndl_msg in rsp.cndl_msg_list:
            dt_ = dt.datetime.strptime(cndl_msg.time, DT_FMT)
            data.append([dt_,
                         cndl_msg.ask_o,
                         cndl_msg.ask_h,
                         cndl_msg.ask_l,
                         cndl_msg.ask_c,
                         cndl_msg.bid_o,
                         cndl_msg.bid_h,
                         cndl_msg.bid_l,
                         cndl_msg.bid_c,
                         cndl_msg.is_complete
                         ])

        df = pd.DataFrame(data)
        df.columns = CANDLE_COL_NAME_LIST
        df = df.set_index(COL_NAME_TIME)

        dftmp = df.loc[:, [COL_NAME_ASK_OP,
                           COL_NAME_ASK_HI,
                           COL_NAME_ASK_LO,
                           COL_NAME_ASK_CL
                           ]]
        dftmp.columns = [CandlestickChart.COL_NAME_OP,
                         CandlestickChart.COL_NAME_HI,
                         CandlestickChart.COL_NAME_LO,
                         CandlestickChart.COL_NAME_CL
                         ]

        self.__csc_gapfill.update(dftmp, gran_id)

    def resize_chart_widget(self):
        fs = self.__ui.widget_chart_gapfill.frameSize()
        self.__csc_gapfill.resize(fs)

    @property
    def inst_id(self):
        return self.__inst_id

    @inst_id.setter
    def inst_id(self, inst_id):
        self.__inst_id = inst_id
