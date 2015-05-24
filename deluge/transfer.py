import zlib

from gevent import socket, ssl
from . import rencode

__all__ = ["DelugeTransfer"]

class DelugeTransfer(object):
    def __init__(self):
        self.conn = None
        self.connected = False

    def connect(self, hostport):
        if self.connected:
            self.disconnect()

        self.sock = socket.create_connection(hostport)
        self.conn = ssl.wrap_socket(self.sock)
        self.connected = True

    def disconnect(self):
        if self.conn:
            self.conn.close()
            self.connected = False

    def send_request(self, request):
        data = (request.format(),)
        payload = zlib.compress(rencode.dumps(data))
        self.conn.write(payload)

    def read_messages(self):
        buf = b""

        while True:
            data = self.conn.read(1024)

            if not data:
                self.connected = False
                break

            buf += data
            dobj = zlib.decompressobj()

            try:
                message = rencode.loads(dobj.decompress(buf))
            except (ValueError, zlib.error):
                # Probably incomplete data, read more
                continue
            else:
                buf = dobj.unused_data

            yield message


