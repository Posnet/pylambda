"""
aws_lambda.wsgi
Amazon Lambda

Copyright (c) 2013 Amazon. All rights reserved.

Lambda wsgi implementation
"""
from __future__ import print_function
try:
    # for python 3
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import urllib.request, urllib.parse, urllib.error
    from urllib.parse import unquote
except ImportError:
    # for python 2
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    import urllib
    from urllib import unquote
import socket
from wsgiref.simple_server import ServerHandler
import sys
import os
import traceback

class FaultData(object):
    """
    Contains three fields, msg, except_value, and trace
    msg is mandatory and must be a string
    except_value and trace are optional and must be a string or None.

    The constructor will convert all values to strings through str().
    In addition, the constructor will try to join iterable trace values with "\n".join.
    """

    def __init__(self, msg, except_value=None, trace=None):
        try:
            trace_is_string = isinstance(trace, basestring)
        except NameError:
            trace_is_string = isinstance(trace, str)
        if not (trace is None or trace_is_string):
            try:
                trace = "\n".join(trace)
            except TypeError:
                trace = str(trace)
        self.msg = str(msg)
        self.except_value = except_value if except_value is None else str(except_value)
        self.trace = trace if trace is None else str(trace)

class FaultException(Exception):
    def __init__(self, msg, except_value=None, trace=None, fatal=False):
        fault_data = FaultData(msg, except_value, trace)
        self.msg = fault_data.msg
        self.except_value = fault_data.except_value
        self.trace = fault_data.trace
        self.fatal = fatal

def handle_one(sockfd, client_addr, app):
    """ This function calls the Request handler. It returns a FaultData object if a fault occurs, else None"""
    try:
        sock = socket.fromfd(sockfd, socket.AF_INET, socket.SOCK_STREAM)
        handler = WSGIGir_RequestHandler(sock, client_addr, app)
        return handler.fault

    except socket.error as e:
        print("Error building a socket object: {}".format(e))
        sys.exit(1)

    finally:
        sock.close()

class Handler(ServerHandler):
    wsgi_run_once = True

    def __init__(self, stdin, stdout, stderr, environ, request_handler):
        """set multithread=False and multiprocess=False"""
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.base_env = environ
        self.request_handler = request_handler # back-pointer for logging
        self.wsgi_multithread = False
        self.wsgi_multiprocess = False
        self.fault = None

    def handle_error(self):
        """Catch errors that occur when serializing the return value to HTTP response and report fault"""

        # There is a bug in some versions of wsgi where code here fails because status is None or environ is None
        self.environ = self.environ or {'SERVER_PROTOCOL' : 'HTTP/1.0'}
        self.status = self.status or "500 Internal server error"
        exc_type, exc_value, exc_traceback = sys.exc_info()
        trace = traceback.format_list(traceback.extract_tb(exc_traceback))
        self.fault = FaultData("Unable to convert result into http response", exc_value, trace)
        ServerHandler.handle_error(self)

    def close(self):
        # There is a bug in some versions of wsgi where code here fails because status is None or environ is None
        self.environ = self.environ or {'SERVER_PROTOCOL' : 'HTTP/1.0'}
        self.status = self.status or "500 Internal server error"
        ServerHandler.close(self)

# define helper function based on the version of python we are running
if sys.version_info[0] < 3:
    def get_content_type_helper(self):
        return self.headers.typeheader
    def get_headers_helper(self):
        return self.headers.headers
    def get_length_helper(self):
        return self.headers.getheader('content-length')
    def parse_header_helper(h):
        k, v = h.split(':', 1)
        return (k , v)
else:
    def get_content_type_helper(self):
        return self.headers.get_content_type()
    def get_headers_helper(self):
        return self.headers.items()
    def get_length_helper(self):
        return self.headers.get('content-length')
    def parse_header_helper(h):
        k, v = h
        return (k , v)

class WSGIGir_RequestHandler(BaseHTTPRequestHandler):
    """WSGI HTTP request handler

    Class which inherits the HTTP request handler base class and takes application as the input.
    Most of the things are taken from wsgiref package's WSGIRequestHandler class.
    """
    def __init__(self, request, client_address, app):
        self.app = app
        self.fault = None
        # set app and call super class constructor
        BaseHTTPRequestHandler.__init__(self, request, client_address, '')

    def get_app(self):
        """This function returns the application which has to be run"""
        return self.app

    def get_environ(self):
        # Set up base environment
        env = {}
        env['CONTENT_LENGTH']=''
        env['GATEWAY_INTERFACE'] = 'CGI/1.1' # TODO we may change this for simple-compute
        env['SCRIPT_NAME'] =  ''
        env['SERVER_PROTOCOL'] = self.request_version
        env['REQUEST_METHOD'] = self.command
        if '?' in self.path:
            path,query = self.path.split('?',1)
        else:
            path,query = self.path,''

        env['PATH_INFO'] = unquote(path)
        env['QUERY_STRING'] = query

        host = self.address_string()
        if host != self.client_address[0]:
            env['REMOTE_HOST'] = host
        env['REMOTE_ADDR'] = self.client_address[0]

        # 2 vs 3
        if get_content_type_helper(self) is None:
            env['CONTENT_TYPE'] = self.headers.type
        else:
            env['CONTENT_TYPE'] = get_content_type_helper(self)

        length = get_length_helper(self)
        if length:
            env['CONTENT_LENGTH'] = length

        for h in get_headers_helper(self):
            (k, v) = parse_header_helper(h)
            k = k.replace('-', '_').upper()
            v = v.strip()
            if k in env:
                continue                    # skip content length, type,etc.
            if 'HTTP_' + k in env:
                env['HTTP_' + k] += ',' + v     # comma-separate multiple headers
            else:
                env['HTTP_' + k] = v
        return env

    def get_stderr(self):
        return sys.stderr

    def send_error(self, code, message=None):
        """Detect errors that occur when reading the HTTP request"""

        if message is None and code in self.responses:
            message = self.responses[code][0]
        self.fault = FaultData("Unable to parse HTTP request", message)
        BaseHTTPRequestHandler.send_error(self, code, message)

    def handle(self):
        """Handle a single HTTP request"""

        self.raw_requestline = self.rfile.readline()
        if not self.parse_request(): #An error code has been sent, just exit
            return

        handler = Handler(
            self.rfile, self.wfile, self.get_stderr(), self.get_environ(), self
        )

        def wrapped_app(environ, start_response):
            """Catch user code exceptions so we can report a fault"""
            try:
                return self.get_app()(environ, start_response)
            except FaultException as e:
                self.fault = FaultData(e.msg, e.except_value, e.trace)
                return handler.error_output(environ, start_response)
            except Exception as e:
                trace = traceback.format_list(traceback.extract_tb(sys.exc_info()[2]))
                self.fault = FaultData("Failure while running task", e, trace[1:])
                return handler.error_output(environ, start_response)
        handler.run(wrapped_app) # pass wrapped application to handler to run it.
        self.fault = self.fault or handler.fault
