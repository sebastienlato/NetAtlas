"""Socket payload accounting, including TLS records, without hidden stream buffers."""

import asyncio
import socket
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import Protocol, TypeVar

from netatlas.config import MeasurementSettings

T = TypeVar("T")


class ByteLimit(Exception):
    pass


@dataclass
class Counters:
    received: int = 0
    sent: int = 0
    retained: int = 0


class Channel(Protocol):
    async def read(self, size: int) -> bytes: ...
    async def write(self, data: bytes) -> None: ...


class SocketChannel:
    def __init__(self, sock: socket.socket, config: MeasurementSettings, count: Counters) -> None:
        self.sock = sock
        self.config = config
        self.count = count

    async def read(self, size: int) -> bytes:
        remaining = self.config.max_response_bytes - self.count.received
        if remaining <= 0:
            raise ByteLimit
        data = await asyncio.get_running_loop().sock_recv(self.sock, min(size, remaining))
        self.count.received += len(data)
        return data

    async def write(self, data: bytes) -> None:
        if len(data) > self.config.max_sent_bytes - self.count.sent:
            raise ByteLimit
        self.count.sent += len(data)  # Reserve before sending, including interrupted sends.
        await asyncio.get_running_loop().sock_sendall(self.sock, data)


class TlsChannel:
    def __init__(self, raw: SocketChannel) -> None:
        self.raw = raw
        self.incoming = ssl.MemoryBIO()
        self.outgoing = ssl.MemoryBIO()
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.set_alpn_protocols(["http/1.1"])
        # No SNI, trust store, client certificate, DNS or verification retry.
        self.ssl = context.wrap_bio(self.incoming, self.outgoing, server_hostname=None)

    async def flush(self) -> None:
        while self.outgoing.pending:
            await self.raw.write(self.outgoing.read())

    async def perform(self, operation: Callable[[], T]) -> T:
        while True:
            try:
                result = operation()
            except ssl.SSLWantReadError:
                await self.flush()
                data = await self.raw.read(4096)
                if data:
                    self.incoming.write(data)
                else:
                    self.incoming.write_eof()
            except ssl.SSLWantWriteError:
                await self.flush()
            else:
                await self.flush()
                return result

    async def read(self, size: int) -> bytes:
        try:
            return await self.perform(lambda: self.ssl.read(size))
        except ssl.SSLZeroReturnError:
            return b""

    async def write(self, data: bytes) -> None:
        offset = 0
        while offset < len(data):
            offset += await self.perform(partial(self.ssl.write, data[offset:]))

    async def handshake(self) -> None:
        await self.perform(self.ssl.do_handshake)
