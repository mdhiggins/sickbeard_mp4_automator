from gevent.event import AsyncResult

import gevent

__all__ = ["DelugeRPCRequest", "DelugeRPCResponse"]

class DelugeRPCRequest(object):
    def __init__(self, request_id, method, *args, **kwargs):
        self.request_id = request_id
        self.method = method
        self.args = args
        self.kwargs = kwargs

    def format(self):
        return (self.request_id, self.method, self.args,
                self.kwargs)


class DelugeRPCResponse(AsyncResult):
    def callback(self, func):
        def cb(res):
            gevent.spawn(func, res.value, res.exception)

        self.rawlink(cb)

