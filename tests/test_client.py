
try:
    import xmlrpclib
except ImportError:
    import xmlrpc.client as xmlrpclib

import mock
import pycurl
import pytest

try:
    import fastrpc
except ImportError:
    fastrpc = None
import tornado_fastrpc.client
from tornado_fastrpc.client import Fault, Result, RpcCall, ServerProxy


@pytest.fixture(scope='function')
def server_proxy():
    return ServerProxy('http://example.com:8000/RPC2')


def test_fault():
    with pytest.raises(Fault) as exc_info:
        raise Fault(-123, "Some error")
    assert "<Fault -123: Some error>" in str(exc_info.value)


def test_result():
    res = Result(True, 123, 456)
    assert res.success is True
    assert res.value == 123
    assert res.exception == 456


def test_rpc_call():
    proxy = mock.Mock()
    call = RpcCall(proxy, 'client')
    call.baz.bar.foo(1, 'abc')
    proxy.call_func.assert_called_once_with('client.baz.bar.foo', 1, 'abc')


def test_init_fail_when_binary_and_not_fastrpc():
    with mock.patch.object(tornado_fastrpc.client, 'fastrpc', new=None):
        with pytest.raises(NotImplementedError) as exc_info:
            ServerProxy('', use_binary=True)
        assert "FastRPC is not supported" in str(exc_info.value)


@pytest.mark.parametrize(
    'patch_attrs, expected_calls',
    [
        (
            {'use_http10': False, 'keep_alive': False},
            [
                mock.call(pycurl.HTTP_VERSION, pycurl.CURL_HTTP_VERSION_1_1),
                mock.call(pycurl.FORBID_REUSE, 1),
                mock.call(pycurl.FRESH_CONNECT, 1),
                mock.call(pycurl.VERBOSE, 0),
                mock.call(pycurl.NOSIGNAL, 1),
            ]
        ),
        (
            {'use_http10': False, 'keep_alive': True},
            [
                mock.call(pycurl.HTTP_VERSION, pycurl.CURL_HTTP_VERSION_1_1),
                mock.call(pycurl.FORBID_REUSE, 0),
                mock.call(pycurl.FRESH_CONNECT, 0),
                mock.call(pycurl.VERBOSE, 0),
                mock.call(pycurl.NOSIGNAL, 1),
            ]
        ),
        (
            {'use_http10': True, 'keep_alive': False},
            [
                mock.call(pycurl.HTTP_VERSION, pycurl.CURL_HTTP_VERSION_1_0),
                mock.call(pycurl.FORBID_REUSE, 1),
                mock.call(pycurl.FRESH_CONNECT, 1),
                mock.call(pycurl.VERBOSE, 0),
                mock.call(pycurl.NOSIGNAL, 1),
            ]
        ),
        (
            {'use_http10': True, 'keep_alive': True},
            [
                mock.call(pycurl.HTTP_VERSION, pycurl.CURL_HTTP_VERSION_1_0),
                mock.call(pycurl.FORBID_REUSE, 0),
                mock.call(pycurl.FRESH_CONNECT, 0),
                mock.call(pycurl.VERBOSE, 0),
                mock.call(pycurl.NOSIGNAL, 1),
            ]
        ),
    ]
)
def test_set_curl_opts(server_proxy, patch_attrs, expected_calls):
    server_proxy.use_http10 = patch_attrs['use_http10']
    server_proxy.keep_alive = patch_attrs['keep_alive']

    m = mock.Mock()
    server_proxy._set_curl_opts(m)
    m.setopt.assert_has_calls(expected_calls, any_order=False)


@pytest.mark.parametrize(
    'kwargs, expected',
    [
        ({}, False),
        ({'quiet': False}, False),
        ({'quiet': True}, True),
    ]
)
def test_get_extra_kwargs(server_proxy, kwargs, expected):
    assert server_proxy._get_extra_kwargs(kwargs) == expected


def test_get_extra_kwargs_fail_when_unknown_argument(server_proxy):
    with pytest.raises(TypeError) as exc_info:
        server_proxy._get_extra_kwargs({'baz': 1})
    assert "got an unexpected keyword argument 'baz'" in str(exc_info.value)


def test_get_post_body_xml(server_proxy):
    with mock.patch.object(tornado_fastrpc.client, 'fastrpc', new=None):
        body = server_proxy._get_post_body('foo', (1, 'abc'))
    assert body == (
        "<?xml version='1.0'?>\n"
        "<methodCall>\n"
        "<methodName>foo</methodName>\n"
        "<params>\n"
        "<param>\n"
        "<value><int>1</int></value>\n"
        "</param>\n"
        "<param>\n"
        "<value><string>abc</string></value>\n"
        "</param>\n"
        "</params>\n"
        "</methodCall>\n"
    )


@pytest.mark.skipif(fastrpc is None, reason="FastRPC is not available")
def test_get_post_body_xml_fastrpc_serializer(server_proxy):
    with mock.patch.object(tornado_fastrpc.client, 'fastrpc', new=fastrpc):
        body = server_proxy._get_post_body('foo', (1, 'abc'))
    assert body == (
        '<?xml version="1.0"?>\n'
        '<!--protocolVersion="2.1"-->\n'
        '<methodCall>\n'
        '<methodName>foo</methodName>\n'
        '<params>\n'
        '<param>\n'
        '<value><i4>1</i4></value>\n'
        '</param>\n'
        '<param>\n'
        '<value><string>abc</string></value>\n'
        '</param>\n'
        '</params>\n'
        '</methodCall>\n'
    )


@pytest.mark.skipif(fastrpc is None, reason="FastRPC is not available")
def test_get_post_body_fastrpc(server_proxy):
    server_proxy.use_binary = True
    with mock.patch.object(tornado_fastrpc.client, 'fastrpc', new=fastrpc):
        body = server_proxy._get_post_body('foo', (1, 'abc'))
    assert body == b'\xca\x11\x02\x01h\x03foo8\x01 \x03abc'


@pytest.mark.parametrize(
    'patch_attrs, expected',
    [
        (
            {
                'ct': 'text/xml',
                'accept': 'text/xml',
                'use_http10': False,
                'keep_alive': True,
            },
            {
                'User-Agent': 'Tornado Async FastRPC client',
                'Host': 'example.com:8000',
                'Content-Type': 'text/xml',
                'Accept': 'text/xml',
                'Accept-Encoding': '',
                'Expect': '100-continue',
            }
        ),
        (
            {
                'ct': 'text/xml',
                'accept': 'text/xml',
                'use_http10': False,
                'keep_alive': False,
            },
            {
                'User-Agent': 'Tornado Async FastRPC client',
                'Host': 'example.com:8000',
                'Content-Type': 'text/xml',
                'Accept': 'text/xml',
                'Accept-Encoding': '',
                'Expect': '100-continue',
                'Connection': 'close',
            }
        ),
        (
            {
                'ct': 'text/xml',
                'accept': 'text/xml',
                'use_http10': True,
                'keep_alive': True,
            },
            {
                'User-Agent': 'Tornado Async FastRPC client',
                'Host': 'example.com:8000',
                'Content-Type': 'text/xml',
                'Accept': 'text/xml',
                'Accept-Encoding': '',
                'Expect': '',
                'Connection': 'keep-alive',
            }
        ),
        (
            {
                'ct': 'text/xml',
                'accept': 'text/xml',
                'use_http10': True,
                'keep_alive': False,
            },
            {
                'User-Agent': 'Tornado Async FastRPC client',
                'Host': 'example.com:8000',
                'Content-Type': 'text/xml',
                'Accept': 'text/xml',
                'Accept-Encoding': '',
                'Expect': '',
            }
        ),
    ]
)
def test_get_headers(server_proxy, patch_attrs, expected):
    for k in patch_attrs:
        setattr(server_proxy, k, patch_attrs[k])
    headers = server_proxy._get_headers()
    assert headers == expected


def test_get_request(server_proxy):
    request_headers = {
        'User-Agent': 'Tornado Async FastRPC client',
        'Host': 'example.com:8000',
        'Content-Type': 'text/xml',
        'Accept': 'text/xml',
        'Accept-Encoding': '',
        'Expect': '100-continue',
    }

    with mock.patch.object(tornado_fastrpc.client, 'fastrpc', new=None):
        with mock.patch.object(server_proxy, '_get_headers') as m_headers:
            with mock.patch.object(server_proxy, '_get_post_body') as m_body:
                m_body.return_value = '1234567890'
                m_headers.return_value = request_headers

                request = server_proxy._get_request('baz.bar', [1, 'abc'])

    assert request.url == 'http://example.com:8000/RPC2'
    assert request.method == 'POST'
    assert request.body.decode('raw_unicode_escape') == '1234567890'
    assert request.request_timeout == 5.0
    assert request.connect_timeout == 5.0
    assert request.proxy_host is None
    assert request.proxy_port is None
    assert request.proxy_username is None
    assert request.proxy_password is None
    assert request.headers == request_headers


@mock.patch.object(tornado_fastrpc.client, 'fastrpc', new=None)
def test_process_rpc_response_xml(server_proxy):
    server_proxy.use_binary = False
    server_proxy.fault_cls = xmlrpclib.Fault

    rpc_response = mock.Mock(
        body=(
            "<?xml version='1.0'?>\n"
            "<methodResponse>\n"
            "<params>\n"
            "<param>\n"
            "<value><int>123</int></value>\n"
            "</param>\n"
            "</params>\n"
            "</methodResponse>\n"
        )
    )
    response = server_proxy._process_rpc_response(rpc_response)

    assert response == 123


@pytest.mark.skipif(fastrpc is None, reason="FastRPC is not available")
@mock.patch.object(tornado_fastrpc.client, 'fastrpc', new=fastrpc)
def test_process_rpc_response_xml_fastrpc_serializer(server_proxy):
    server_proxy.use_binary = False
    server_proxy.fault_cls = fastrpc.Fault

    rpc_response = mock.Mock(
        body=(
            '<?xml version="1.0"?>\n'
            '<!--protocolVersion="2.1"-->\n'
            '<methodResponse>\n'
            '<params>\n'
            '<param>\n'
            '<value><i4>456</i4></value>\n'
            '</param>\n</params>\n'
            '</methodResponse>\n'
        )
    )
    response = server_proxy._process_rpc_response(rpc_response)

    assert response == 456


@pytest.mark.skipif(fastrpc is None, reason="FastRPC is not available")
@mock.patch.object(tornado_fastrpc.client, 'fastrpc', new=fastrpc)
def test_process_rpc_response_fastrpc(server_proxy):
    server_proxy.use_binary = True
    server_proxy.fault_cls = fastrpc.Fault

    rpc_response = mock.Mock(body=b'\xca\x11\x02\x01p9\x15\x03')
    response = server_proxy._process_rpc_response(rpc_response)

    assert response == 789


@mock.patch.object(tornado_fastrpc.client, 'fastrpc', new=None)
def test_process_rpc_response_xml_fail(server_proxy):
    server_proxy.use_binary = False
    server_proxy.fault_cls = xmlrpclib.Fault

    rpc_response = mock.Mock(
        body=(
            "<?xml version='1.0'?>\n"
            "<methodResponse>\n"
            "<fault>\n"
            "<value><struct>\n"
            "<member>\n"
            "<name>faultCode</name>\n"
            "<value><int>-123</int></value>\n"
            "</member>\n"
            "<member>\n"
            "<name>faultString</name>\n"
            "<value><string>Foo</string></value>\n"
            "</member>\n"
            "</struct></value>\n"
            "</fault>\n"
            "</methodResponse>\n"
        )
    )
    with pytest.raises(Fault) as exc_info:
        server_proxy._process_rpc_response(rpc_response)
    assert "<Fault -123: Foo>" in str(exc_info.value)


@pytest.mark.skipif(fastrpc is None, reason="FastRPC is not available")
@mock.patch.object(tornado_fastrpc.client, 'fastrpc', new=fastrpc)
def test_process_rpc_response_fastrpc_fail(server_proxy):
    server_proxy.use_binary = False
    server_proxy.fault_cls = fastrpc.Fault

    with pytest.raises(Fault) as exc_info:
        rpc_response = mock.Mock(body=b'\xca\x11\x02\x01x@{ \x03Foo')
        server_proxy._process_rpc_response(rpc_response)
    assert "<Fault -123: Foo>" in str(exc_info.value)
