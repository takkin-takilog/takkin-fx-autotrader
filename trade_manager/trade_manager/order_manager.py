import datetime as dt
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from trade_manager_msgs.msg import (MarketOrderRequest,
                                    LimitOrderRequest,
                                    StopOrderRequest)
from api_msgs.srv import (OrderCreateSrv, TradeDetailsSrv,
                          TradeCRCDOSrv, TradeCloseSrv,
                          OrderDetailsSrv, OrderCancelSrv)
from api_msgs.msg import OrderType as OrderTypeMsg
from api_msgs.msg import OrderState as OrderStateMsg
from system_tests_msgs.msg import StateTest

_DT_FMT = "%Y-%m-%d %H:%M:%S"


class OrderState(object):

    ORDER_TYP_MARKET = 1
    ORDER_TYP_LIMIT = 2
    ORDER_TYP_STOP = 3

    STS_NEW_ORD_WAIT_RSP = 1        # 新規注文リクエスト応答待ち
    STS_NEW_ORD_PENDING = 2         # 新規注文保留状態
    STS_NEW_ORD_DET_WAIT_RSP = 3    # 注文詳細取得リクエスト応答待ち
    STS_NEW_ORD_CNC_REQ = 4         # 新規注文キャンセルリクエスト応答待ち
    STS_SET_ORD_PENDING = 5         # 決済注文キャンセル応答待ち
    STS_TRADE_DET_WAIT_RSP = 6      # トレード詳細取得リクエスト応答待ち
    STS_TRADE_CLS_WAIT_RSP = 7      # トレードクローズリクエスト応答待ち
    STS_END = 255                   # 終了

    def __init__(self, order_typ, msg, future, logger):

        self.__logger = logger

        self.__req_id = msg.req_id
        self.__order_typ = order_typ
        self.__sts = OrderState.STS_NEW_ORD_WAIT_RSP
        self.__future = future
        self.__order_id = 0
        self.__trade_id = 0

        self.__inst_id = msg.instrument_id
        self.__units = msg.units
        self.__price = msg.price

        if not msg.valid_period_new:
            self.__dt_new = None
        else:
            self.__dt_new = dt.datetime.strptime(
                msg.valid_period_new, _DT_FMT)
        self.__tp_price = msg.take_profit_price
        self.__sl_price = msg.stop_loss_price

        if not msg.valid_period_settlement:
            self.__dt_settlement = None
        else:
            self.__dt_settlement = dt.datetime.strptime(
                msg.valid_period_settlement, _DT_FMT)

    @property
    def request_id(self):
        return self.__req_id

    @property
    def state(self):
        return self.__sts

    @property
    def future(self):
        return self.__future

    @future.setter
    def future(self, future):
        self.__future = future

    @property
    def order_id(self):
        return self.__order_id

    @property
    def trade_id(self):
        return self.__trade_id

    def update(self, pol_flg):
        if self.__sts == OrderState.STS_NEW_ORD_WAIT_RSP:
            self.__check_future_by_order_create()
        elif self.__sts == OrderState.STS_NEW_ORD_PENDING:
            self.__check_state_new_order_pending(pol_flg)
        elif self.__sts == OrderState.STS_NEW_ORD_DET_WAIT_RSP:
            self.__check_future_by_order_details()
        elif self.__sts == OrderState.STS_NEW_ORD_CNC_REQ:
            self.__check_future_by_order_cancel()
        elif self.__sts == OrderState.STS_SET_ORD_PENDING:
            self.__check_state_settlement_order_pending(pol_flg)
        elif self.__sts == OrderState.STS_TRADE_DET_WAIT_RSP:
            self.__check_future_by_trade_details()
        elif self.__sts == OrderState.STS_TRADE_CLS_WAIT_RSP:
            self.__check_future_by_trade_close()
        else:
            pass

    def __check_future_by_order_create(self):

        if self.__future.done():
            rsp = self.__future.result()
            if rsp is None:
                e = self.__future.exception()
                raise RuntimeError("Exception while calling service of node")
            else:
                if rsp.result is True:
                    if self.__order_typ == OrderState.ORDER_TYP_MARKET:
                        self.__trade_id = rsp.id
                        # change state: 1 -> 5
                        self.__logger.debug("----- [change state: 1 -> 5]")
                        self.__sts = OrderState.STS_SET_ORD_PENDING
                    else:
                        self.__order_id = rsp.id
                        # change state: 1 -> 2
                        self.__logger.debug("----- [change state: 1 -> 2]")
                        self.__sts = OrderState.STS_NEW_ORD_PENDING
                else:
                    print("Service request Failed!")
                    # TODO: process at failed

    def __check_state_new_order_pending(self, pol_flg):

        if pol_flg is True:
            # change state: 2 -> 3
            self.__logger.debug("----- [change state: 2 -> 3]")
            self.__sts = OrderState.STS_NEW_ORD_DET_WAIT_RSP
        elif self.__dt_new is not None:
            dt_now = dt.datetime.now()
            self.__logger.debug(
                "----- [new_order_pending] %s < %s" % (self.__dt_new, dt_now))
            if self.__dt_new < dt_now:
                self.__logger.debug("----- [new_order_pending]datetime over")
                # change state: 2 -> 3
                self.__logger.debug("----- [change state: 2 -> 3]")
                self.__sts = OrderState.STS_NEW_ORD_DET_WAIT_RSP

    def __check_future_by_order_details(self):

        if self.__future.done():
            rsp = self.__future.result()
            if rsp is None:
                e = self.__future.exception()
                raise RuntimeError("Exception while calling service of node")
            else:
                if rsp.result is True:
                    if rsp.order_state_msg.state == OrderStateMsg.STS_FILLED:
                        self.__trade_id = rsp.open_trade_id
                        # change state: 3 -> 5
                        self.__logger.debug("----- [change state: 3 -> 5]")
                        self.__sts = OrderState.STS_SET_ORD_PENDING
                    elif rsp.order_state_msg.state == OrderStateMsg.STS_PENDING:
                        if self.__dt_new is not None:
                            dt_now = dt.datetime.now()
                            self.__logger.debug(
                                "----- [order_details] %s < %s" % (self.__dt_new, dt_now))
                            if self.__dt_new < dt_now:
                                self.__logger.debug(
                                    "----- [order_details]datetime over")
                                # change state: 3 -> 4
                                self.__logger.debug(
                                    "----- [change state: 3 -> 4]")
                                self.__sts = OrderState.STS_NEW_ORD_CNC_REQ
                            else:
                                # change state: 3 -> 2
                                self.__logger.debug(
                                    "----- [change state: 3 -> 2]")
                                self.__sts = OrderState.STS_NEW_ORD_PENDING
                        else:
                            # change state: 3 -> 2
                            self.__logger.debug("----- [change state: 3 -> 2]")
                            self.__sts = OrderState.STS_NEW_ORD_PENDING
                else:
                    print("Service request Failed!")
                    # TODO: process at failed

    def __check_future_by_order_cancel(self):

        if self.__future.done():
            rsp = self.__future.result()
            if rsp is None:
                e = self.__future.exception()
                raise RuntimeError("Exception while calling service of node")
            else:
                if rsp.result is True:
                    # change state: 4 -> END
                    self.__logger.debug("----- [change state: 4 -> END]")
                    self.__sts = OrderState.STS_END
                else:
                    print("Service request Failed!")
                    # TODO: process at failed

    def __check_state_settlement_order_pending(self, pol_flg):

        if pol_flg is True:
            # change state: 5 -> 6
            self.__logger.debug("----- [change state: 5 -> 6]")
            self.__sts = OrderState.STS_TRADE_DET_WAIT_RSP
        elif self.__dt_settlement is not None:
            dt_now = dt.datetime.now()
            self.__logger.debug(
                "----- [settlement_order_pending] %s < %s" % (self.__dt_settlement, dt_now))
            if self.__dt_settlement < dt_now:
                self.__logger.debug(
                    "----- [settlement_order_pending]datetime over")
                # change state: 5 -> 6
                self.__logger.debug("----- [change state: 5 -> 6]")
                self.__sts = OrderState.STS_TRADE_DET_WAIT_RSP

    def __check_future_by_trade_details(self):

        if self.__future.done():
            rsp = self.__future.result()
            if rsp is None:
                e = self.__future.exception()
                raise RuntimeError("Exception while calling service of node")
            else:
                if rsp.result is True:
                    if rsp.order_state_msg.state == OrderStateMsg.STS_FILLED:
                        # change state: 6 -> END
                        self.__logger.debug("----- [change state: 6 -> END]")
                        self.__sts = OrderState.STS_END
                    elif rsp.order_state_msg.state == OrderStateMsg.STS_PENDING:
                        dt_now = dt.datetime.now()
                        self.__logger.debug(
                            "----- [trade_details] %s < %s" % (self.__dt_settlement, dt_now))
                        if self.__dt_settlement < dt_now:
                            self.__logger.debug(
                                "----- [trade_details]datetime over")
                            # change state: 6 -> 7
                            self.__logger.debug("----- [change state: 6 -> 7]")
                            self.__sts = OrderState.STS_TRADE_CLS_WAIT_RSP
                        else:
                            # change state: 6 -> 5
                            self.__logger.debug("----- [change state: 6 -> 5]")
                            self.__sts = OrderState.STS_SET_ORD_PENDING
                else:
                    print("Service request Failed!")
                    # TODO: process at failed

    def __check_future_by_trade_close(self):

        if self.__future.done():
            rsp = self.__future.result()
            if rsp is None:
                e = self.__future.exception()
                raise RuntimeError("Exception while calling service of node")
            else:
                if rsp.result is True:
                    # change state: 7 -> END
                    self.__logger.debug("----- [change state: 7 -> END]")
                    self.__sts = OrderState.STS_END
                else:
                    print("Service request Failed!")
                    # TODO: process at failed


class OrderManager(Node):

    def __init__(self):
        super().__init__("order_manager")

        # Set logger lebel
        self.__logger = super().get_logger()
        self.__logger.set_level(rclpy.logging.LoggingSeverity.DEBUG)

        TPCNM_MARKET_ORDER_REQUEST = "market_order_request"
        TPCNM_LIMIT_ORDER_REQUEST = "limit_order_request"
        TPCNM_STOP_ORDER_REQUEST = "stop_order_request"
        TPCNM_POLLING = "polling"

        # Declare publisher and subscriber
        msg_type = MarketOrderRequest
        topic = TPCNM_MARKET_ORDER_REQUEST
        callback = self.__on_recv_market_order_request
        self.__sub_mrk_req = self.create_subscription(msg_type,
                                                      topic,
                                                      callback)
        msg_type = LimitOrderRequest
        topic = TPCNM_LIMIT_ORDER_REQUEST
        callback = self.__on_recv_limit_order_request
        self.__sub_lim_req = self.create_subscription(msg_type,
                                                      topic,
                                                      callback)
        msg_type = StopOrderRequest
        topic = TPCNM_STOP_ORDER_REQUEST
        callback = self.__on_recv_stop_order_request
        self.__sub_stp_req = self.create_subscription(msg_type,
                                                      topic,
                                                      callback)

        msg_type = Bool
        topic = TPCNM_POLLING
        callback = self.__on_recv_polling
        self.__sub_stp_req = self.create_subscription(msg_type,
                                                      topic,
                                                      callback)

        # Create service client "OrderCreate"
        srv_type = OrderCreateSrv
        srv_name = "order_create"
        self.__cli_ordcre = self.__create_service_client(srv_type, srv_name)

        # Create service client "TradeDetails"
        srv_type = TradeDetailsSrv
        srv_name = "trade_details"
        self.__cli_tradet = self.__create_service_client(srv_type, srv_name)

        # Create service client "TradeCRCDO"
        srv_type = TradeCRCDOSrv
        srv_name = "trade_crcdo"
        self.__cli_tracrc = self.__create_service_client(srv_type, srv_name)

        # Create service client "TradeClose"
        srv_type = TradeCloseSrv
        srv_name = "trade_close"
        self.__cli_tracls = self.__create_service_client(srv_type, srv_name)

        # Create service client "OrderDetails"
        srv_type = OrderDetailsSrv
        srv_name = "order_details"
        self.__cli_orddet = self.__create_service_client(srv_type, srv_name)

        # Create service client "OrderCancel"
        srv_type = OrderCancelSrv
        srv_name = "order_cancel"
        self.__cli_ordcnc = self.__create_service_client(srv_type, srv_name)

        self.__ordlist = []

        self.__timer_10sec = self.create_timer(1, self.__on_timeout_10sec)

        # for debug
        msg_type = StateTest
        topic = "state_test"
        self.__pub_ststest = self.create_publisher(msg_type, topic)

    def __on_timeout_10sec(self):
        #self.__logger.debug("========== Time out[1s] ==========")
        self.__update_state()

    def __update_state(self, pol_flg=False):

        #self.__logger.debug("--- 注文OBJ個数:%d" % len(self.__ordlist))

        ordlist = self.__ordlist
        for idx, order in enumerate(ordlist):
            self.__logger.debug("----- 注文OBJ[%d]" % (idx + 1))
            pre_sts = order.state
            # Update order state.
            order.update(pol_flg)
            # change state action.
            self.__change_state_action(order, pre_sts)

            #self.__logger.debug("----- 状態[%d]" % order.state)

            # for debug
            msg = StateTest()
            msg.req_id = order.request_id
            msg.state = order.state
            msg.order_id = order.order_id
            msg.trade_id = order.trade_id
            self.__pub_ststest.publish(msg)

        # remove end state
        self.__ordlist = [o for o in ordlist if o.state != OrderState.STS_END]

    def __change_state_action(self, order, pre_sts):

        if pre_sts == OrderState.STS_NEW_ORD_PENDING:
            if order.state == OrderState.STS_NEW_ORD_DET_WAIT_RSP:
                # change state: 2 -> 3
                req = OrderDetailsSrv.Request()
                req.order_id = order.order_id
                order.future = self.__cli_orddet.call_async(req)
        elif pre_sts == OrderState.STS_NEW_ORD_DET_WAIT_RSP:
            if order.state == OrderState.STS_NEW_ORD_CNC_REQ:
                # change state: 3 -> 4
                req = OrderCancelSrv.Request()
                req.order_id = order.order_id
                order.future = self.__cli_ordcnc.call_async(req)
        elif pre_sts == OrderState.STS_SET_ORD_PENDING:
            if order.state == OrderState.STS_TRADE_DET_WAIT_RSP:
                # change state: 5 -> 6
                req = TradeDetailsSrv.Request()
                req.trade_id = order.trade_id
                order.future = self.__cli_tradet.call_async(req)
        elif pre_sts == OrderState.STS_TRADE_DET_WAIT_RSP:
            if order.state == OrderState.STS_TRADE_CLS_WAIT_RSP:
                # change state: 6 -> 7
                req = TradeCloseSrv.Request()
                req.trade_id = order.trade_id
                order.future = self.__cli_tracls.call_async(req)
        else:
            pass

    def __create_service_client(self, srv_type, srv_name):
        # Create service client
        cli = self.create_client(srv_type, srv_name)
        # Wait for a service server
        ready = cli.wait_for_service(timeout_sec=1.0)
        if not ready:
            raise RuntimeError("Wait for service timed out")
        return cli

    def __on_recv_market_order_request(self, msg):
        self.__logger.debug("topic rcv:%s" % msg)

    def __on_recv_limit_order_request(self, msg):
        dt_now = dt.datetime.now().strftime(_DT_FMT)
        self.__logger.debug(
            "---------- [Topic Rcv]<Limit>Start: %s" % (dt_now))

        req = OrderCreateSrv.Request()
        req.ordertype_msg.type = OrderTypeMsg.TYP_LIMIT
        req.inst_msg.instrument_id = msg.instrument_id
        req.units = msg.units
        req.price = msg.price
        req.take_profit_price = msg.take_profit_price
        req.stop_loss_price = msg.stop_loss_price
        future = self.__cli_ordcre.call_async(req)

        order_typ = OrderState.ORDER_TYP_LIMIT
        obj = OrderState(order_typ, msg, future, self.__logger)
        self.__ordlist.append(obj)

    def __on_recv_stop_order_request(self, msg):
        self.__logger.debug("topic rcv:%s" % msg)

    def __on_recv_polling(self, msg):
        if msg.data is True:
            self.__update_state(True)


def main(args=None):
    rclpy.init(args=args)
    order_manager = OrderManager()

    try:
        rclpy.spin(order_manager)
    except KeyboardInterrupt:
        pass

    order_manager.destroy_node()
    rclpy.shutdown()