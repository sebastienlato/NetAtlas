"""Deterministic bounded sampling, prefix fairness and explicit new refresh identities."""

from collections import Counter, defaultdict, deque
from datetime import timedelta
from ipaddress import ip_address, ip_network

from netatlas.derivations.engine import canonical, digest
from netatlas.discovery.policy import POLICY_SHA256
from netatlas.domain import Endpoint
from netatlas.scheduler.models import Entry, Plan, PlanningInput, Source


def rank(seed: int, value: str) -> str:
    return digest(f"coverage-refresh-1\n{seed}\n{value}".encode("ascii"))


def plan(request: PlanningInput) -> Plan:
    request = PlanningInput.model_validate(request.model_dump())
    universe, policy, settings = request.universe, request.policy, request.settings.measurement
    if not universe.valid_from <= request.at < universe.expires_at:
        raise ValueError("universe is not current at planning clock")
    input_hash = digest(canonical(request))
    counts: Counter[str] = Counter(
        {
            key: 0
            for key in (
                "ipv4_routed_addresses",
                "ipv4_unrouted_addresses",
                "ipv4_unknown_addresses",
                "ipv6_routed_regions",
                "ipv6_unrouted_regions",
                "ipv6_unknown_regions",
                "ipv6_routed_seeds",
                "ipv6_nonrouted_seeds",
                "ipv6_seedless_routed_regions",
                "candidate_endpoints",
                "excluded",
                "blocked",
                "fresh",
                "eligible",
                "sampled_out",
                "queue_deferred",
                "scheduled",
                "coverage",
                "refresh",
                "expired_history",
            )
        }
    )
    latest: dict[str, Source] = {}
    for source in request.history:
        if source.finished_at + timedelta(days=30) <= request.at:
            counts["expired_history"] += 1
            continue
        old = latest.get(source.endpoint.key)
        if old is None or (source.finished_at, source.started_at, source.observation_id.int) > (
            old.finished_at,
            old.started_at,
            old.observation_id.int,
        ):
            latest[source.endpoint.key] = source
    blocked = {endpoint.key for endpoint in request.blocked}
    denied = (
        *settings.exclusion_cidrs,
        *settings.opt_out_cidrs,
        *(ip_network(n) for n in request.suppressions),
    )
    groups: dict[str, list[Entry]] = defaultdict(list)
    for region in universe.regions:
        network = ip_network(region.network)
        seeds = {s.address: s for s in universe.seeds if ip_address(s.address) in network}
        if network.version == 4:
            counts[f"ipv4_{region.state}_addresses"] += network.num_addresses
        else:
            counts[f"ipv6_{region.state}_regions"] += 1
            counts["ipv6_routed_seeds" if region.state == "routed" else "ipv6_nonrouted_seeds"] += (
                len(seeds)
            )
            if region.state == "routed" and not seeds:
                counts["ipv6_seedless_routed_regions"] += 1
        if region.state != "routed":
            continue
        addresses = tuple(network) if network.version == 4 else tuple(map(ip_address, seeds))
        for candidate in addresses:
            address = ip_address(str(candidate))
            for port in universe.ports:
                counts["candidate_endpoints"] += 1
                endpoint = Endpoint(address=address, port=port)
                if any(address in n for n in denied) or (
                    settings.allow_cidrs and not any(address in n for n in settings.allow_cidrs)
                ):
                    counts["excluded"] += 1
                    continue
                if endpoint.key in blocked:
                    counts["blocked"] += 1
                    continue
                previous = latest.get(endpoint.key)
                due = request.at
                if previous:
                    interval = {
                        "open": policy.open_seconds,
                        "closed": policy.closed_seconds,
                        "timeout": policy.uncertain_seconds,
                        "error": policy.uncertain_seconds,
                    }[previous.outcome.value]
                    due = previous.finished_at + timedelta(seconds=interval)
                    if due > request.at:
                        counts["fresh"] += 1
                        continue
                counts["eligible"] += 1
                prefix = str(
                    ip_network(f"{address}/{24 if address.version == 4 else 48}", strict=False)
                )
                identity = digest(f"{input_hash}\n{endpoint.key}".encode("ascii"))
                groups[prefix].append(
                    Entry(
                        identity=identity,
                        endpoint=endpoint,
                        prefix=prefix,
                        region=region.network,
                        origin_id=region.origin_id,
                        seed_origin_id=seeds[str(address)].origin_id
                        if address.version == 6
                        else None,
                        shard=int(rank(policy.seed, "shard:" + endpoint.key), 16) % policy.shards,
                        kind="refresh" if previous else "coverage",
                        due_at=due,
                        previous=previous,
                    )
                )
    queues: dict[str, deque[Entry]] = {}
    for prefix, entries in groups.items():
        # Overdue retained sources first within each prefix; ties/unseen use SHA ordering.
        entries.sort(
            key=lambda entry: (
                entry.due_at,
                rank(policy.seed, entry.endpoint.key),
                entry.endpoint.key,
            )
        )
        counts["sampled_out"] += max(0, len(entries) - policy.sample_per_prefix)
        queues[prefix] = deque(entries[: policy.sample_per_prefix])
    order = sorted(queues, key=lambda prefix: (rank(policy.seed, prefix), prefix))
    if order:
        offset = policy.round % len(order)
        order = order[offset:] + order[:offset]
    scheduled: list[Entry] = []
    capacity = min(policy.queue_size, settings.queue_size, 128)
    while order and len(scheduled) < capacity:
        next_round = []
        for prefix in order:
            if len(scheduled) == capacity:
                break
            scheduled.append(queues[prefix].popleft())
            if queues[prefix]:
                next_round.append(prefix)
        order = next_round
    counts["queue_deferred"] = sum(len(q) for q in queues.values())
    counts["scheduled"] = len(scheduled)
    counts.update(entry.kind for entry in scheduled)
    return Plan(
        input_sha256=input_hash,
        universe_sha256=digest(canonical(universe)),
        policy_sha256=digest(canonical(policy)),
        seeds_sha256=digest(b"\n".join(canonical(s) for s in universe.seeds)),
        config_sha256=request.settings.sha256,
        connection_policy_sha256=POLICY_SHA256,
        at=request.at,
        expires_at=request.expires_at,
        counts=dict(sorted(counts.items())),
        entries=tuple(scheduled),
    )
