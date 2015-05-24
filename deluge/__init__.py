"""An implementation of the Deluge RPC protocol using gevent.

Example usage:

    from geventdeluge import DelgueClient

    client = DelugeClient()
    client.connect()

    # Wait for value
    download_location = client.core.get_config_value("download_location").get()

    def on_get_config_value(value, key):
        print "Got config value from the daemon!"
        print "%s: %s" % (key, value)

        client.disconnect()

    # Callback style
    client.core.get_config_value("download_location").callback(on_get_config_value, "download_location")

    # Wait for event loop to finish
    client.run()

"""


__title__ = "gevent-deluge"
__version__ = "0.1"
__license__ = "Simplified BSD"
__author__ = "Christopher Rosell"
__copyright__ = "Copyright 2013 Christopher Rosell"

from .client import DelugeClient
from .exceptions import DelugeRPCError

