tornado-fastrpc
===============

Non-blocking *FastRPC* (see https://github.com/seznam/fastrpc) client
for *Python's Tornado*. If *FastRPC* is not available, only *XML-RPC*
protocol will be supported. *Python 2.7* and *Python 3.4* (or higher)
are supported.

Instalation
-----------

Requirements:

+ *pycurl*
+ *Tornado* 3.2 or higher

Optional requirements:

+ *fastrpc* (*libfastrpc* + *fastrpc* module)

::

    cd tornado-fastrpc/
    python setup.py install

Ussage
------

::

    class MainHandler(tornado.web.RequestHandler):
        @tornado.gen.coroutine
        def get(self):
            try:
                res = yield proxy.getData(123)
            except Exception as e:
                self.write('Error: {}'.format(e))
            else:
                self.write('Data: {}'.format(res.value))

or::

    class MainHandler(tornado.web.RequestHandler):
        @tornado.gen.coroutine
        def get(self):
            res = yield proxy.getData(123, quiet=True)
            if res.success:
                self.write('Data: {}'.format(res.value))
            else:
                self.write('Error: {}'.format(res.exception))

License
-------

3-clause BSD
