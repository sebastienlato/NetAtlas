"""Pinned conservative policy, without DNS or runtime registry downloads.

IANA IPv4/IPv6 special-purpose registries, both last updated 2025-10-09,
reviewed 2026-10-04. All listed blocks are denied, including global exceptions.
Contained registry rows are collapsed into their denied parent prefix.
Sources: https://www.iana.org/assignments/iana-ipv4-special-registry/
         https://www.iana.org/assignments/iana-ipv6-special-registry/
"""

import hashlib
from ipaddress import IPv4Address, IPv6Address, ip_network

from netatlas.config import MeasurementSettings

POLICY_VERSION = "connect-policy-1"
REGISTRY_VERSION = "iana-special-2025-10-09-reviewed-2026-10-04"
SPECIAL_CIDRS = (
    "0.0.0.0/8",
    "10.0.0.0/8",
    "100.64.0.0/10",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "192.0.0.0/24",
    "192.0.2.0/24",
    "192.31.196.0/24",
    "192.52.193.0/24",
    "192.88.99.0/24",
    "192.168.0.0/16",
    "192.175.48.0/24",
    "198.18.0.0/15",
    "198.51.100.0/24",
    "203.0.113.0/24",
    "240.0.0.0/4",
    "::/128",
    "::1/128",
    "::ffff:0:0/96",
    "64:ff9b::/96",
    "64:ff9b:1::/48",
    "100::/64",
    "100:0:0:1::/64",
    "2001::/23",
    "2001:db8::/32",
    "2002::/16",
    "2620:4f:8000::/48",
    "3fff::/20",
    "5f00::/16",
    "fc00::/7",
    "fe80::/10",
)
SPECIAL_NETWORKS = tuple(ip_network(value) for value in SPECIAL_CIDRS)
POLICY_SHA256 = hashlib.sha256(
    (POLICY_VERSION + REGISTRY_VERSION + "\n".join(SPECIAL_CIDRS)).encode()
).hexdigest()
type Address = IPv4Address | IPv6Address


def denial(address: Address, settings: MeasurementSettings, *, lab: bool = False) -> str | None:
    """Denials win over allowlists, including in the explicit loopback fixture mode."""
    if isinstance(address, IPv6Address) and address.scope_id is not None:
        return "scoped_address"
    if any(address in network for network in settings.exclusion_cidrs):
        return "excluded"
    if any(address in network for network in settings.opt_out_cidrs):
        return "opt_out"
    if lab:
        if str(address) not in {"127.0.0.1", "::1"}:
            return "outside_loopback_lab"
    else:
        if address.is_multicast:
            return "multicast"
        if any(address in network for network in SPECIAL_NETWORKS):
            return "special_use"
        if not address.is_global or address.is_reserved or address.is_unspecified:
            return "non_global"
        # Fail closed outside the currently allocated IPv6 global-unicast space.
        if address.version == 6 and address not in ip_network("2000::/3"):
            return "outside_ipv6_global_unicast"
    if settings.allow_cidrs and not any(address in network for network in settings.allow_cidrs):
        return "outside_allowlist"
    return None
