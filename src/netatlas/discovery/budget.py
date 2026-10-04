"""One shared, no-burst pacer for all tasks in a campaign."""

import asyncio
from collections.abc import Awaitable, Callable
from ipaddress import ip_network

from netatlas.discovery.policy import Address


class Budget:
    def __init__(
        self,
        global_rate: float,
        prefix_rate: float,
        *,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.global_interval = 1 / global_rate
        self.prefix_interval = 1 / prefix_rate
        self.clock = clock or asyncio.get_running_loop().time
        self.sleep = sleep
        self.lock = asyncio.Lock()
        self.next_global = 0.0
        self.next_prefix: dict[str, float] = {}

    async def acquire(self, address: Address) -> None:
        prefix = str(ip_network(f"{address}/{24 if address.version == 4 else 48}", strict=False))
        # Holding the lock while sleeping prevents reservations becoming bursts
        # after scheduler delays; cancelled waiters do not consume future tokens.
        async with self.lock:
            while True:
                now = self.clock()
                delay = max(self.next_global, self.next_prefix.get(prefix, 0)) - now
                if delay <= 0:
                    self.next_global = now + self.global_interval
                    self.next_prefix[prefix] = now + self.prefix_interval
                    return
                await self.sleep(delay)
