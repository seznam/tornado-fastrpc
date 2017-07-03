
===============
tornado-fastrpc
===============

Non-blocking XML-RPC and FastRPC (see https://github.com/seznam/fastrpc)
client for Python's Tornado. If FastRPC is not available, only XML-RPC
protocol will be supported. Python 2.7 and Python 3.4 (or higher) are
supported.

Instalation
-----------

Requirements:

+ *pycurl*
+ *Tornado* 3.2 or higher

Optional requirements:

+ *fastrpc* (*libfastrpc* + *fastrpc* Python's module)

Instalation and tests:

::

    python setup.py install
    python setup.py test

Build Debian Jessie package (requires ``dpkg-buildpackage`` + ``lintian``
and dependencies in ``Build-Depends`` option in ``debian/control`` file.
Before building package, checkout debian-* branch.

::

    python setup.py bdist_deb

Ussage
------

::

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

Documentation
-------------

ServerProxy class
`````````````````

*class* tornado_fastrpc.client.\ **ServerProxy**\(*uri,
connect_timeout=5.0, timeout=5.0, use_binary=False, user_agent=None,
keep_alive=False, use_http10=True, http_proxy=None, max_clients=10*)

    Async FastRPC client for Tornado, tt uses ``pycurl`` backend.
    Manages communication with a remote RPC server.

    - **url** *<string>*
          URL address
    - **connect_timeout** *<float>*
          Timeout for initial connection in seconds
    - **request_timeout** *<float>*
          Timeout for entire request in seconds
    - **use_binary** *<bool>*
          Force binary protocol
    - **user_agent** *<string>*
          User-Agent string
    - **keep_alive** *<bool>*
          Allow keep-alive connection
    - **use_http10** *<bool>*
          Force HTTP/1.0 protocol instead of HTTP/1.1
    - **http_proxy** *<string>*
          HTTP proxy, eg. http://user:pass@example.com:80
    - **max_clients** *<int>*
          Size of the Curl's connection pool

Result object
`````````````

*class* tornado_fastrpc.client.\ **Result**\(*success, value, exception*)

Return type for FastRPC call. Contains attributes:

    - **success** *<bool>*
          ``True`` if operation succeeded, else ``False``
    - **value**
          contains returning value if operation succeeded, else ``None``
    - **exception** *<bool>*
          contains instance of the exception if operation failed, else ``None``

Fault object
````````````

*class* tornado_fastrpc.client.\ **Fault**\(*faultCode, faultString*)

    Exception, indicates an XML-RPC error.

    - **faultCode** *<string>*
          Error code
    - **faultString** *<string>*
          Error message

License
-------

3-clause BSD
