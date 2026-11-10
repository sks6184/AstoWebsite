"""IPv4 binding for direct OpenAI connections, scoped to these client instances."""
import httpx
from openai import DefaultHttpxClient


class IPv4HttpClient(DefaultHttpxClient):
    """Preserve SDK defaults, TLS and HTTPX proxy routing; bind direct sockets.

    HTTPX disables environment proxy discovery when a custom transport is passed
    to its constructor. Overriding only its transport initializer preserves that
    discovery, NO_PROXY, CA environment settings and explicit test transports.
    Proxy transports intentionally retain HTTPX's original proxy behavior.
    """

    def _init_transport(self, *, verify, cert, trust_env, http1, http2, limits, transport):
        if transport is not None:
            return transport
        return httpx.HTTPTransport(verify=verify, cert=cert, trust_env=trust_env,
            http1=http1, http2=http2, limits=limits, local_address='0.0.0.0', retries=0)

    def __del__(self):
        # Match the SDK's default SyncHttpxClientWrapper cleanup for legacy callers.
        try:
            if not self.is_closed:
                self.close()
        except Exception:
            pass
