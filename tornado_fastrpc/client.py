"""
Async HTTP client based on Tornado's AsyncHTTPClient.

Usage::

    proxy = ServerProxy('http://example.com/RPC2:8000',
                        connect_timeout=5.0,
                        timeout=5.0,
                        use_binary=True)


    class BazHandler(tornado.web.RequestHandler):

        @tornado.gen.coroutine
        def get(self):
            try:
                res = yield proxy.getData(123)
            except Exception as e:
                self.write('Error: {}'.format(e))
            else:
                self.write('Data: {}'.format(res.value))


    class BarHandler(tornado.web.RequestHandler):

        @tornado.gen.coroutine
        def get(self):
            res = yield proxy.getData(123, quiet=True)
            if res.success:
                self.write('Data: {}'.format(res.value))
            else:
                self.write('Error: {}'.format(res.exception))
"""

import collections
try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse
try:
    import xmlrpc.client as xmlrpclib
except ImportError:
    import xmlrpclib

try:
    import fastrpc
except ImportError:
    fastrpc = None
import pycurl
import tornado.curl_httpclient
import tornado.gen

__all__ = ['Fault', 'Result', 'ServerProxy']


class Fault(Exception):
    """
    Indicates an XML-RPC error.
    """

    def __init__(self, code, msg):
        super(Fault, self).__init__()
        self.faultCode = code
        self.faultString = msg

    def __str__(self):
        return "<{} {}: {}>".format(
            self.__class__.__name__, self.faultCode, self.faultString
        )


Result = collections.namedtuple('Result', ['success', 'value', 'exception'])
"""
Return type for FastRPC call. Contains attributes *success*, *value* and
*exception*.

* *success* is :const:`True` if operation succeeded, else :const:`False`
* *value* contains returning value if operation succeeded, else :const:`None`
* *exception* contains instance of the exception if operation failed,
  else :const:`None`
"""


class RpcCall(object):
    """
    Encapsulates RPC call. :class:`ServerProxy` uses this class for
    calling RPC methods using dotted path ``proxy.baz.bar(1, 2, 3)``
    instead of proxy.call_func('bar', 1, 2, 3).
    """

    def __init__(self, proxy, initial_call_path=''):
        self._proxy = proxy
        self._path = [initial_call_path] if initial_call_path else []

    def __call__(self, *args, **kwargs):
        return self._proxy.call_func('.'.join(self._path), *args, **kwargs)

    def __getattr__(self, name):
        self._path.append(name)
        return self


class ServerProxy(object):
    """
    Async **FastRPC** client for **Tornado**. It uses **pycurl** backend.
    Manages communication with a remote RPC server.
    """

    user_agent = 'Tornado Async FastRPC client'
    http_client_cls = tornado.curl_httpclient.CurlAsyncHTTPClient

    def __init__(self, uri, connect_timeout=5.0, timeout=5.0,
                 use_binary=False, user_agent=None, keep_alive=False,
                 use_http10=True, http_proxy=None, max_clients=10):
        """
        All parameters except *url* are optional.

        :arg string url: URL address
        :arg float connect_timeout: Timeout for initial connection in seconds
        :arg float request_timeout: Timeout for entire request in seconds
        :arg bool use_binary: Force binary protocol
        :arg string user_agent: User-Agent string
        :arg bool keep_alive: Allow keep-alive connection
        :arg bool use_http10: Force HTTP/1.0 protocol instead of HTTP/1.1
        :arg string http_proxy: HTTP proxy, eg. http://user:pass@example.com:80
        :arg int max_clients: Size of the Curl's connection pool
        """
        # Check FastRPC support
        if use_binary and fastrpc is None:
            raise NotImplementedError("FastRPC is not supported")

        self.uri = uri
        self.host = urlparse.urlparse(uri).netloc
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self.use_binary = use_binary
        self.content_type = 'application/x-frpc' if use_binary else 'text/xml'
        if fastrpc:
            self.accept = 'application/x-frpc, text/xml'
            self.fault_cls = fastrpc.Fault
        else:
            self.accept = 'text/xml'
            self.fault_cls = xmlrpclib.Fault
        if user_agent is not None:
            self.user_agent = user_agent
        self.keep_alive = keep_alive
        self.use_http10 = use_http10
        if http_proxy:
            p = urlparse.urlparse(http_proxy)
            self.proxy_host = p.hostname
            self.proxy_port = p.port or 80
            self.proxy_username = p.username
            self.proxy_password = p.password
        else:
            self.proxy_host = None
            self.proxy_port = None
            self.proxy_username = None
            self.proxy_password = None
        self.max_clients = max_clients

        self._http_client_inst = None

    @property
    def _http_client(self):
        # Must be property, because instance of the CurlAsyncHTTPClient
        # must be created lazy. The reason is that instance of the
        # tornado.ioloop.IOLoop mustn't be created before server is
        # forked.
        if self._http_client_inst is None:
            self._http_client_inst = self.http_client_cls(
                max_clients=self.max_clients
            )
        return self._http_client_inst

    def _set_curl_opts(self, c):
        # Method is called by libcurl, c argument is pycurl.Curl object, see
        # http://www.tornadoweb.org/en/stable/httpclient.html#request-objects
        if self.use_http10:
            c.setopt(pycurl.HTTP_VERSION, pycurl.CURL_HTTP_VERSION_1_0)
        else:
            c.setopt(pycurl.HTTP_VERSION, pycurl.CURL_HTTP_VERSION_1_1)
        if self.keep_alive is True:
            c.setopt(pycurl.FORBID_REUSE, 0)
            c.setopt(pycurl.FRESH_CONNECT, 0)
        else:
            c.setopt(pycurl.FORBID_REUSE, 1)
            c.setopt(pycurl.FRESH_CONNECT, 1)
        c.setopt(pycurl.VERBOSE, 0)
        # https://ravidhavlesha.wordpress.com/2012/01/08/curl-timeout-problem-and-solution/
        c.setopt(pycurl.NOSIGNAL, 1)

    def _get_extra_kwargs(self, kwargs):
        quiet = kwargs.pop('quiet', False)
        if kwargs:
            arg_name = kwargs.popitem()[0]
            raise TypeError(
                "got an unexpected keyword argument '{}'".format(arg_name)
            )
        return (quiet,)

    def _get_post_body(self, name, args):
        if fastrpc is not None:
            return fastrpc.dumps(args, name, useBinary=self.use_binary)
        else:
            return xmlrpclib.dumps(args, name, allow_none=True)

    def _get_headers(self):
        headers = {
            'User-Agent': self.user_agent,
            'Host': self.host,
            'Content-Type': self.content_type,
            'Accept': self.accept,
            'Accept-Encoding': '',
        }
        if self.use_http10 is True:
            # Disable Expect header if HTTP/1.0 protocol is used because
            # if server doesn't send response, curl will wait 100 ms.
            headers['Expect'] = ''
        else:
            # If HTTP/1.1 protocol is used, will send 'Expect: 100 Continue'
            # header because if POST method and keep-alive is used, curl
            # will wait cca 40 ms and keep-alive requests are too slow.
            headers['Expect'] = '100-continue'
        if self.use_http10 is True and self.keep_alive is True:
            headers['Connection'] = 'keep-alive'
        if self.use_http10 is False and self.keep_alive is False:
            headers['Connection'] = 'close'
        return headers

    def _get_request(self, name, args):
        return tornado.httpclient.HTTPRequest(
            self.uri,
            method='POST',
            body=self._get_post_body(name, args),
            request_timeout=self.timeout,
            connect_timeout=self.connect_timeout,
            prepare_curl_callback=self._set_curl_opts,
            proxy_host=self.proxy_host,
            proxy_port=self.proxy_port,
            proxy_username=self.proxy_username,
            proxy_password=self.proxy_password,
            headers=self._get_headers()
        )

    def _process_rpc_response(self, response):
        try:
            if fastrpc is not None:
                response_data = fastrpc.loads(response.body)[0]
            else:
                response_data = xmlrpclib.loads(response.body)[0][0]
        except self.fault_cls as e:
            raise Fault(e.faultCode, e.faultString)
        else:
            return response_data

    @tornado.gen.coroutine
    def call_func(self, name, *args, **kwargs):
        """
        Call RPC function *name* with arguments *args*. If *quiet* is
        :const:`True`, call never raises an exception and return value
        is instance of the exception.

        ::

            res = yield proxy.call_func('div', 4, 2)
            res = yield proxy.call_func('div', 4, 0, quiet=True)
        """
        (quiet,) = self._get_extra_kwargs(kwargs)
        try:
            request = self._get_request(name, args)
            response = yield self._http_client.fetch(request)
            result_data = self._process_rpc_response(response)
        except Exception as e:
            if quiet:
                raise tornado.gen.Return(Result(False, None, e))
            else:
                raise
        else:
            raise tornado.gen.Return(Result(True, result_data, None))

    def __getattr__(self, name):
        return RpcCall(self, name)
