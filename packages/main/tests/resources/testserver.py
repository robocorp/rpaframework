# Initially based on:
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/336012

import os
import threading

try:
    from httplib import HTTPConnection
    from BaseHTTPServer import HTTPServer
    from SimpleHTTPServer import SimpleHTTPRequestHandler
    from SocketServer import ThreadingMixIn
except ImportError:  # Python 3
    from http.client import HTTPConnection
    from http.server import SimpleHTTPRequestHandler, HTTPServer
    from socketserver import ThreadingMixIn


class StoppableHttpRequestHandler(SimpleHTTPRequestHandler):
    """http request handler with QUIT stopping the server"""

    def do_QUIT(self):
        self.send_response(200)
        self.end_headers()
        self.server.shutdown()
        self.server.server_close()

    def do_POST(self):
        self.do_GET()


class ThreadingHttpServer(ThreadingMixIn, HTTPServer):
    pass


def start_server():
    path = os.path.dirname(os.path.abspath(__file__))
    os.chdir(path)
    server = ThreadingHttpServer(("", 7000), StoppableHttpRequestHandler)
    server.serve_forever()


if __name__ == "__main__":
    threading.Thread(target=start_server)
