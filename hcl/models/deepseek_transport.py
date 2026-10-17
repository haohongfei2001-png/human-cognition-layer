"""One fixed TLS HTTP/1.1 exchange, no SDK/proxy/redirect/retry or key discovery.

The embedding host supplies an already-authorized secure credential provider.
No constructor accepts a key, environment variable name, arbitrary URL, TLS
context or connection factory. Tests intercept the connection at the socket
boundary and route it exclusively to loopback; there is no fixture/live flag.
"""
import asyncio
import ssl
from contextlib import AbstractContextManager
from typing import Protocol
from hcl.models.deepseek_contracts import ENDPOINT, MAX_REQUEST_BYTES, MAX_RESPONSE_BYTES
from hcl.kernel.types import HCLFailure


# RFC 9110 sections 5.3/12.5.5 and RFC 9111 section 5.2 permit these
# response fields on multiple lines. This client has no cookie jar or HTTP
# cache: discard every occurrence, without combining, retaining or forwarding
# values. All other duplicate names remain fail-closed, especially framing,
# representation metadata and unknown extension fields.
_IGNORED_REPEATABLE_HEADERS = frozenset({"set-cookie", "vary", "cache-control"})
_FIELD_NAME_CHARS = frozenset("!#$%&'*+-.^_`|~0123456789abcdefghijklmnopqrstuvwxyz")


class HostCredentialProvider(Protocol):
    def borrow_bearer(self, endpoint: str) -> AbstractContextManager[str]:
        """Borrow a credential for this exact destination; never log/cache it."""
        ...


class DeepSeekTransportFailure(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class DeepSeekHTTPTransport:
    def __init__(self, credential_provider, *, connect_timeout=10.0, absolute_timeout=120.0):
        if not callable(getattr(credential_provider, "borrow_bearer", None)):
            raise ValueError("explicit host credential provider required")
        if any(type(v) not in (int,float) or not 0 < v <= 180 for v in (connect_timeout, absolute_timeout)):
            raise ValueError("bounded positive timeouts required")
        if connect_timeout > absolute_timeout:
            raise ValueError("connect timeout cannot exceed absolute timeout")
        self._credentials = credential_provider
        self._connect_timeout, self._absolute_timeout = connect_timeout, absolute_timeout

    async def send(self, body, before_write):
        """before_write atomically gates durable batch/grant/ACL immediately before bytes.

        No await separates the successful gate from writer.write. Cancellation,
        disconnect or timeout afterwards has unknown billing, never a safe retry.
        """
        if type(body) is not str or len(body.encode("utf-8")) > MAX_REQUEST_BYTES:
            raise DeepSeekTransportFailure("DEEPSEEK_REQUEST_CAPACITY")
        writer = None
        deadline = asyncio.get_running_loop().time() + self._absolute_timeout
        def check_deadline():
            if asyncio.get_running_loop().time() >= deadline:
                raise DeepSeekTransportFailure("DEEPSEEK_ABSOLUTE_TIMEOUT")
        try:
            async with asyncio.timeout(self._absolute_timeout):
                context = ssl.create_default_context()
                reader, writer = await asyncio.wait_for(asyncio.open_connection(
                    "api.deepseek.com", 443, ssl=context, server_hostname="api.deepseek.com",
                    limit=16384), self._connect_timeout)
                check_deadline()
                with self._credentials.borrow_bearer(ENDPOINT) as bearer:
                    check_deadline()
                    if (type(bearer) is not str or not 1 <= len(bearer) <= 4096
                            or any(ord(c) < 33 or ord(c) > 126 for c in bearer)):
                        raise DeepSeekTransportFailure("DEEPSEEK_CREDENTIAL_UNAVAILABLE")
                    payload = body.encode("utf-8")
                    head = ("POST /chat/completions HTTP/1.1\r\nHost: api.deepseek.com\r\n"
                            "Content-Type: application/json\r\nAccept: application/json\r\n"
                            "Accept-Encoding: identity\r\nConnection: close\r\n"
                            "Authorization: Bearer " + bearer + "\r\nContent-Length: " + str(len(payload)) + "\r\n\r\n")
                    before_write()
                    check_deadline()
                    writer.write(head.encode("ascii") + payload)
                    del bearer, head
                    await writer.drain()
                header = await reader.readuntil(b"\r\n\r\n")
                if len(header) > 16384:
                    raise DeepSeekTransportFailure("DEEPSEEK_HEADER_CAPACITY")
                lines = header.decode("ascii").split("\r\n")
                status = lines[0].split(" ", 2)
                if len(status) < 2 or status[0] != "HTTP/1.1" or len(status[1]) != 3 or not status[1].isdigit():
                    raise DeepSeekTransportFailure("DEEPSEEK_HTTP_INVALID")
                code = int(status[1])
                if code != 200:
                    raise DeepSeekTransportFailure("DEEPSEEK_HTTP_"+str(code))
                headers = {}
                for line in lines[1:-2]:
                    name, sep, value = line.partition(":")
                    name = name.lower()
                    # Validate even ignored lines before discarding them. Only
                    # SP/HTAB are whitespace in field values; reject controls,
                    # bare CR/LF, obsolete folding and non-token field names.
                    if (not sep or not name or any(c not in _FIELD_NAME_CHARS for c in name)
                            or any((ord(c) < 32 and c != "\t") or ord(c) == 127 for c in value)):
                        raise DeepSeekTransportFailure("DEEPSEEK_HEADERS_INVALID")
                    if name in _IGNORED_REPEATABLE_HEADERS:
                        continue
                    if name in headers:
                        raise DeepSeekTransportFailure("DEEPSEEK_HEADERS_INVALID")
                    headers[name] = value.strip(" \t")
                if headers.get("content-type", "").split(";",1)[0].lower() != "application/json":
                    raise DeepSeekTransportFailure("DEEPSEEK_CONTENT_TYPE_INVALID")
                if headers.get("content-encoding", "identity").lower() != "identity":
                    raise DeepSeekTransportFailure("DEEPSEEK_ENCODING_INVALID")
                length, transfer = headers.get("content-length"), headers.get("transfer-encoding")
                if length is not None and transfer is not None:
                    raise DeepSeekTransportFailure("DEEPSEEK_FRAMING_INVALID")
                if length is not None:
                    if not length.isdigit() or len(length) > 12 or int(length) > MAX_RESPONSE_BYTES:
                        raise DeepSeekTransportFailure("DEEPSEEK_RESPONSE_CAPACITY")
                    return await reader.readexactly(int(length))
                result = bytearray()
                if transfer is not None:
                    if transfer.lower() != "chunked":
                        raise DeepSeekTransportFailure("DEEPSEEK_FRAMING_INVALID")
                    while True:
                        line = await reader.readuntil(b"\r\n")
                        if len(line) > 16 or not line[:-2] or any(c not in b"0123456789abcdefABCDEF" for c in line[:-2]):
                            raise DeepSeekTransportFailure("DEEPSEEK_CHUNK_INVALID")
                        count = int(line[:-2], 16)
                        if count == 0:
                            if await reader.readexactly(2) != b"\r\n":
                                raise DeepSeekTransportFailure("DEEPSEEK_TRAILERS_DENIED")
                            break
                        if len(result)+count > MAX_RESPONSE_BYTES:
                            raise DeepSeekTransportFailure("DEEPSEEK_RESPONSE_CAPACITY")
                        result.extend(await reader.readexactly(count))
                        if await reader.readexactly(2) != b"\r\n":
                            raise DeepSeekTransportFailure("DEEPSEEK_CHUNK_INVALID")
                else:
                    while True:
                        part = await reader.read(min(65536, MAX_RESPONSE_BYTES+1-len(result)))
                        if not part:
                            break
                        result.extend(part)
                        if len(result) > MAX_RESPONSE_BYTES:
                            raise DeepSeekTransportFailure("DEEPSEEK_RESPONSE_CAPACITY")
                return bytes(result)
        except DeepSeekTransportFailure:
            raise
        except HCLFailure:
            raise  # Trusted gate diagnostics contain no credential or response text.
        except Exception:
            raise DeepSeekTransportFailure("DEEPSEEK_TRANSPORT_UNKNOWN") from None
        finally:
            if writer is not None:
                writer.close()  # Do not let TLS shutdown extend the absolute deadline.
