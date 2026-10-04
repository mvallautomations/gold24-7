"""
Live Execution Blocker: Permanently disallows any live broker order execution.
Raises fatal exception on any execution call to guarantee live funds cannot be traded.
"""


class LiveExecutionForbiddenError(RuntimeError):
    """Raised whenever any component attempts live order placement."""
    pass


class LiveBrokerAdapterDisabled:
    """
    Stub adapter replacing any live MT5 order placement functions.
    Hardwired to reject 100% of order dispatch requests.
    """

    def __init__(self):
        self.is_live = False

    def order_send(self, *args, **kwargs):
        raise LiveExecutionForbiddenError(
            "FATAL SAFETY VIOLATION: Live order execution is permanently disabled in GOLD24-7 research architecture. "
            "System is strictly authorized for SIMULATION_ONLY and PAPER TRADING."
        )

    def buy(self, *args, **kwargs):
        return self.order_send()

    def sell(self, *args, **kwargs):
        return self.order_send()

    def modify_position(self, *args, **kwargs):
        return self.order_send()

    def close_position(self, *args, **kwargs):
        return self.order_send()
