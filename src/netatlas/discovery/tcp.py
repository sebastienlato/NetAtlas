"""A numeric-address TCP connect only. No reads, writes, DNS, or retries."""

import asyncio
import errno
import socket

from netatlas.domain import Endpoint, Outcome


async def connect(endpoint: Endpoint, timeout: float) -> tuple[Outcome, str | None]:
    family = socket.AF_INET if endpoint.address.version == 4 else socket.AF_INET6
    try:
        # Own the raw socket for its entire lifetime, including cancelled connects.
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.setblocking(False)
            async with asyncio.timeout(timeout):
                await asyncio.get_running_loop().sock_connect(
                    sock, (str(endpoint.address), endpoint.port)
                )
        return Outcome.OPEN, None
    except TimeoutError:
        return Outcome.TIMEOUT, "connect_timeout"
    except OSError as exc:
        if exc.errno == errno.ECONNREFUSED:
            return Outcome.CLOSED, "connection_refused"
        if exc.errno == errno.ETIMEDOUT:
            return Outcome.TIMEOUT, "connect_timeout"
        if exc.errno in {errno.ENETUNREACH, errno.EHOSTUNREACH}:
            return Outcome.ERROR, "network_unreachable"
        if exc.errno in {errno.EACCES, errno.EPERM}:
            return Outcome.ERROR, "local_permission_denied"
        return Outcome.ERROR, "socket_error"
