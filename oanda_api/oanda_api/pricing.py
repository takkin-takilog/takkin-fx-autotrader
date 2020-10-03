from typing import TypeVar
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSHistoryPolicy, QoSReliabilityPolicy
from std_msgs.msg import Bool
from api_msgs.msg import PriceBucket, Pricing, Instrument
from oandapyV20 import API
from oandapyV20.endpoints import pricing as pr
from oandapyV20.exceptions import V20Error
from oanda_api.service_common import INST_DICT

MsgType = TypeVar("MsgType")


class PricingPublisher(Node):

    def __init__(self) -> None:
        super().__init__("pricing")

        # Set logger lebel
        logger = super().get_logger()
        logger.set_level(rclpy.logging.LoggingSeverity.DEBUG)

        PRMNM_ACCOUNT_NUMBER = "account_number"
        PRMNM_ACCESS_TOKEN = "ACCESS_TOKEN"
        ENA_INST = "enable_instrument."
        PRMNM_ENA_INST_USDJPY = ENA_INST + "usdjpy"
        PRMNM_ENA_INST_EURJPY = ENA_INST + "eurjpy"
        PRMNM_ENA_INST_EURUSD = ENA_INST + "eurusd"

        TPCNM_PRICING_USDJPY = "pricing_usdjpy"
        TPCNM_PRICING_EURJPY = "pricing_eurjpy"
        TPCNM_PRICING_EURUSD = "pricing_eurusd"
        TPCNM_ACT_FLG = "activate_flag"

        # Declare parameter
        self.declare_parameter(PRMNM_ACCOUNT_NUMBER)
        self.declare_parameter(PRMNM_ACCESS_TOKEN)
        self.declare_parameter(PRMNM_ENA_INST_USDJPY)
        self.declare_parameter(PRMNM_ENA_INST_EURJPY)
        self.declare_parameter(PRMNM_ENA_INST_EURUSD)

        ACCOUNT_NUMBER = self.get_parameter(PRMNM_ACCOUNT_NUMBER).value
        ACCESS_TOKEN = self.get_parameter(PRMNM_ACCESS_TOKEN).value
        ENA_INST_USDJPY = self.get_parameter(PRMNM_ENA_INST_USDJPY).value
        ENA_INST_EURJPY = self.get_parameter(PRMNM_ENA_INST_EURJPY).value
        ENA_INST_EURUSD = self.get_parameter(PRMNM_ENA_INST_EURUSD).value

        logger.debug("[Param]Account Number:[{}]".format(ACCOUNT_NUMBER))
        logger.debug("[Param]Access Token:[{}]".format(ACCESS_TOKEN))
        logger.debug("[Param]Enable instrument:")
        logger.debug("        USD/JPY:[{}]".format(ENA_INST_USDJPY))
        logger.debug("        EUR/JPY:[{}]".format(ENA_INST_EURJPY))
        logger.debug("        EUR/USD:[{}]".format(ENA_INST_EURUSD))

        # Declare publisher and subscriber
        qos_profile = QoSProfile(history=QoSHistoryPolicy.KEEP_ALL,
                                 reliability=QoSReliabilityPolicy.RELIABLE)
        inst_name_list = []
        self._pub_dict = {}
        if ENA_INST_USDJPY:
            inst_name = INST_DICT[Instrument.INST_USD_JPY].name
            pub = self.create_publisher(Pricing,
                                        TPCNM_PRICING_USDJPY,
                                        qos_profile)
            self._pub_dict[inst_name] = pub.publish
            inst_name_list.append(inst_name)
        if ENA_INST_EURJPY:
            inst_name = INST_DICT[Instrument.INST_EUR_JPY].name
            pub = self.create_publisher(Pricing,
                                        TPCNM_PRICING_EURJPY,
                                        qos_profile)
            self._pub_dict[inst_name] = pub.publish
            inst_name_list.append(inst_name)
        if ENA_INST_EURUSD:
            inst_name = INST_DICT[Instrument.INST_EUR_USD].name
            pub = self.create_publisher(Pricing,
                                        TPCNM_PRICING_EURUSD,
                                        qos_profile)
            self._pub_dict[inst_name] = pub.publish
            inst_name_list.append(inst_name)

        callback = self._on_subs_act_flg
        self.__sub_act = self.create_subscription(Bool,
                                                  TPCNM_ACT_FLG,
                                                  callback,
                                                  qos_profile)

        # Initialize
        self._act_flg = False
        self._api = API(ACCESS_TOKEN=ACCESS_TOKEN)

        instruments = ",".join(inst_name_list)
        params = {"instruments": instruments}
        self._pi = pr.PricingInfo(ACCOUNT_NUMBER, params)

        self._logger = logger

    def background(self) -> None:

        while self._act_flg:
            try:
                self._request()
            except V20Error as e:
                self._logger.error("!!!!!!!!!! V20Error !!!!!!!!!!")
                self._logger.error("{}".format(e))

            rclpy.spin_once(self, timeout_sec=0)

    def _on_subs_act_flg(self, msg: MsgType) -> None:
        if msg.data:
            self._act_flg = True
        else:
            self._act_flg = False

    def _request(self) -> None:

        rsp = self._api.request(self._pi)
        price_list = rsp["prices"]
        for price in price_list:
            if price["type"] == "PRICE":
                msg = Pricing()
                msg.time = price["time"]
                for bid in price["bids"]:
                    pb = PriceBucket()
                    pb.price = float(bid["price"])
                    pb.liquidity = bid["liquidity"]
                    msg.bids.append(pb)
                for ask in price["asks"]:
                    pb = PriceBucket()
                    pb.price = float(ask["price"])
                    pb.liquidity = ask["liquidity"]
                    msg.asks.append(pb)
                msg.closeout_bid = float(price["closeoutBid"])
                msg.closeout_ask = float(price["closeoutAsk"])
                msg.tradeable = price["tradeable"]
                # Publish topics
                self._pub_dict[price["instrument"]](msg)


def main(args=None):
    rclpy.init(args=args)
    pricing_api = PricingPublisher()

    try:
        while rclpy.ok():
            rclpy.spin_once(pricing_api, timeout_sec=1.0)
            pricing_api.background()
    except KeyboardInterrupt:
        pass

    pricing_api.destroy_node()
    rclpy.shutdown()