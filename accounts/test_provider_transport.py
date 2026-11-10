"""Offline regressions for scoped IPv4, TLS, authentication and provider defaults."""
import os
import socket
import ssl
from unittest.mock import patch

import httpx
from openai import OpenAI, APIConnectionError, DEFAULT_CONNECTION_LIMITS, DEFAULT_TIMEOUT
from django.test import SimpleTestCase

from .provider_transport import IPv4HttpClient


class ProviderTransportTests(SimpleTestCase):
    def test_direct_transport_binds_ipv4_and_verifies_hostname_and_certificate(self):
        with IPv4HttpClient(trust_env=False) as client:
            pool = client._transport._pool
            self.assertEqual(pool._local_address, '0.0.0.0')
            self.assertTrue(pool._ssl_context.check_hostname)
            self.assertEqual(pool._ssl_context.verify_mode, ssl.CERT_REQUIRED)
            self.assertEqual(pool._retries, 0)

    def test_sdk_defaults_and_explicit_timeout_retries_are_preserved(self):
        with IPv4HttpClient(trust_env=False) as transport:
            self.assertEqual(transport.timeout, DEFAULT_TIMEOUT)
            self.assertTrue(transport.follow_redirects)
            pool = transport._transport._pool
            self.assertEqual(pool._max_connections, DEFAULT_CONNECTION_LIMITS.max_connections)
            self.assertEqual(pool._max_keepalive_connections, DEFAULT_CONNECTION_LIMITS.max_keepalive_connections)
            with OpenAI(api_key='synthetic-key', http_client=transport, timeout=20, max_retries=0) as api:
                self.assertEqual(api.timeout, 20)
                self.assertEqual(api.max_retries, 0)

    def test_environment_proxy_and_no_proxy_are_preserved(self):
        with patch.dict(os.environ, {'HTTPS_PROXY': 'http://127.0.0.1:9999', 'NO_PROXY': 'example.test'}, clear=True):
            with IPv4HttpClient() as client:
                direct = client._transport
                self.assertIsNot(client._transport_for_url(httpx.URL('https://api.openai.com')), direct)
                self.assertIs(client._transport_for_url(httpx.URL('https://example.test')), direct)

    def test_custom_ca_context_is_preserved(self):
        context = ssl.create_default_context()
        with IPv4HttpClient(verify=context, trust_env=False) as client:
            self.assertIs(client._transport._pool._ssl_context, context)

    def test_sdk_authentication_hostname_and_timeout_reach_custom_transport(self):
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={'data': [], 'object': 'list'})

        mock_transport = httpx.MockTransport(respond)
        with IPv4HttpClient(transport=mock_transport, trust_env=False) as transport:
            self.assertIs(transport._transport, mock_transport)
            with OpenAI(api_key='synthetic-key', http_client=transport, timeout=20, max_retries=0) as api:
                api.models.list()
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].url.host, 'api.openai.com')
        self.assertEqual(requests[0].url.scheme, 'https')
        self.assertEqual(requests[0].headers['authorization'], 'Bearer synthetic-key')
        self.assertEqual(requests[0].extensions['timeout'], dict(connect=20, read=20, write=20, pool=20))

    def test_certificate_failure_is_not_bypassed_or_retried(self):
        attempts = []

        def reject(request):
            attempts.append(1)
            raise httpx.ConnectError('Synthetic certificate rejection', request=request) from ssl.SSLCertVerificationError()

        with IPv4HttpClient(transport=httpx.MockTransport(reject), trust_env=False) as transport:
            with OpenAI(api_key='synthetic-key', http_client=transport, max_retries=0) as api:
                with self.assertRaises(APIConnectionError):
                    api.models.list()
        self.assertEqual(attempts, [1])

    def test_ipv6_first_dns_never_attempts_ipv6_connect_when_bound_to_ipv4(self):
        connects, binds = [], []

        class FakeSocket:
            def __init__(self, family, *args): self.family = family
            def settimeout(self, timeout): pass
            def bind(self, address):
                binds.append((self.family, address))
                if self.family == socket.AF_INET6:
                    raise OSError('IPv4 source cannot bind IPv6 socket')
            def connect(self, address): connects.append((self.family, address))
            def setsockopt(self, *args): pass
            def close(self): pass

        candidates = [(socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('::1', 443, 0, 0)),
                      (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443))]
        with IPv4HttpClient(trust_env=False) as transport:
            pool = transport._transport._pool
            with patch('socket.getaddrinfo', return_value=candidates), patch('socket.socket', side_effect=FakeSocket):
                stream = pool._network_backend.connect_tcp('api.openai.com', 443, timeout=20,
                                                           local_address=pool._local_address)
                stream.close()
        self.assertEqual(connects, [(socket.AF_INET, ('127.0.0.1', 443))])
        self.assertEqual(binds[0], (socket.AF_INET6, ('0.0.0.0', 0)))

    def test_client_close_releases_transport(self):
        client = IPv4HttpClient(trust_env=False)
        client.close()
        self.assertTrue(client.is_closed)
