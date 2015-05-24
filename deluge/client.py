import os
import gevent

from collections import defaultdict
from gevent.pool import Group
from itertools import imap

from .exceptions import DelugeRPCError
from .protocol import DelugeRPCRequest, DelugeRPCResponse
from .transfer import DelugeTransfer

__all__ = ["DelugeClient"]


RPC_RESPONSE = 1
RPC_ERROR = 2
RPC_EVENT = 3


class DelugeClient(object):
    def __init__(self, disconnect=None, restore_events=False):
        """A deluge client session.

        :param disconnect: func, a disconnect callback, called when connection is dropped
        :param restore_events: bool, keep event handlers on re-connect
        """

        self.transfer = DelugeTransfer()

        self.modules = []
        self.restore_events = restore_events

        self._event_handlers = defaultdict(list)
        self._disconnect_handler = disconnect
        self._greenlets = Group()
        self._responses = {}
        self._request_counter = 0

    def _get_local_auth(self):
        xdg_config = os.path.expanduser(os.environ.get("XDG_CONFIG_HOME",
                                                       "~/.config"))
        config_home = os.path.join(xdg_config, "deluge")
        auth_file = os.path.join(config_home, "auth")

        username = password = ""
        with open(auth_file) as fd:
            for line in fd:
                if line.startswith("#"):
                    continue

                auth = line.split(":")
                if len(auth) >= 2 and auth[0] == "localclient":
                    username, password = auth[0], auth[1]
                    break

        return username, password

    def _transfer_message(self, message):
        self.transfer.transfer_message((message.format(),))

    def _create_module_method(self, module, method):
        fullname = "{0}.{1}".format(module, method)

        def func(obj, *args, **kwargs):
            return self._call(fullname, *args, **kwargs)

        func.__name__ = method

        return func

    def _introspect(self):
        self.modules = []

        methods = self._call("daemon.get_method_list").get()
        methodmap = defaultdict(dict)
        splitter = lambda v: v.split(".")

        for module, method in imap(splitter, methods):
            methodmap[module][method] = self._create_module_method(module, method)

        for module, methods in methodmap.items():
            clsname = "DelugeModule{0}".format(module.capitalize())
            cls = type(clsname, (), methods)
            setattr(self, module, cls())
            self.modules.append(module)

    def _restore_events(self):
        self._call("daemon.set_event_interest", self._event_handlers.keys()).get()

    def _handle_message(self, message):
        if not isinstance(message, tuple):
            return

        if len(message) < 3:
            return

        message_type = message[0]

        if message_type == RPC_EVENT:
            event = message[1]
            values = message[2]

            if event in self._event_handlers:
                for handler in self._event_handlers[event]:
                    gevent.spawn(handler, *values)

        elif message_type in (RPC_RESPONSE, RPC_ERROR):
            request_id = message[1]
            value = message[2]

            if request_id in self._responses:
                response = self._responses[request_id]

                if message_type == RPC_RESPONSE:
                    response.set(value)
                elif message_type == RPC_ERROR:
                    err = DelugeRPCError(*value)
                    response.set_exception(err)

                del self._responses[request_id]

    def _wait_for_messages(self):
        for message in self.transfer.read_messages():
            self._handle_message(message)

        if self._disconnect_handler:
            self._disconnect_handler(self)

    def _call(self, method, *args, **kwargs):
        req = DelugeRPCRequest(self._request_counter, method,
                               *args, **kwargs)

        self.transfer.send_request(req)

        response = DelugeRPCResponse()
        self._responses[self._request_counter] = response
        self._request_counter += 1

        return response

    def connect(self, host="127.0.0.1", port=58846,
                username="", password=""):
        """Connects to a daemon process.

        :param host: str, the hostname of the daemon
        :param port: int, the port of the daemon
        :param username: str, the username to login with
        :param password: str, the password to login with
        """

        if not self.restore_events:
            self._event_handlers.clear()

        # Connect transport
        self.transfer.connect((host, port))

        # Start a message listener
        self._greenlets.spawn(self._wait_for_messages)

        # Attempt to fetch local auth info if needed
        if not username and host in ("127.0.0.1", "localhost"):
            username, password = self._get_local_auth()

        # Authenticate
        self._call("daemon.login", username, password).get()

        # Introspect available methods
        self._introspect()

        # Keep event handlers if specified
        if self.restore_events:
            self._restore_events()

    @property
    def connected(self):
        return self.transfer.connected

    def disconnect(self):
        """Disconnects from the daemon."""
        self.transfer.disconnect()

    def register_event(self, event, handler):
        """Registers a handler that will be called when an event is received from the daemon.

        :params event: str, the event to handle
        :params handler: func, the handler function, f(args)
        """

        self._event_handlers[event].append(handler)

        return self._call("daemon.set_event_interest", [event])

    def run(self):
        """Blocks until all event loops are done."""

        self._greenlets.join()


