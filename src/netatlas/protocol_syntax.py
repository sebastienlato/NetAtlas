"""Small syntax-based collectors. Protocol recognition never uses port numbers."""

import re
from dataclasses import dataclass
from typing import Protocol as CollectorProtocol

from netatlas.domain import Protocol
from netatlas.evidence import HttpMetadata, SmtpMetadata, SshMetadata


@dataclass
class Parsed:
    done: bool = False
    status: str = "unknown"
    http: HttpMetadata | None = None
    ssh: SshMetadata | None = None
    smtp: SmtpMetadata | None = None
    candidates: tuple[Protocol, ...] = ()


class Collector(CollectorProtocol):
    """Incremental, bounded evidence parser; selection and I/O are separate."""

    def accepts(self, data: bytes) -> bool: ...
    def inspect(self, data: bytes, *, eof: bool = False) -> Parsed: ...


class HttpCollector:
    def accepts(self, data: bytes) -> bool:
        return data.startswith(b"HTTP/")

    def inspect(self, data: bytes, *, eof: bool = False) -> Parsed:
        line, separator, rest = data.partition(b"\r\n")
        if not separator:
            return Parsed(done=eof or len(data) >= 8192, status="malformed")
        match = re.fullmatch(rb"HTTP/(1\.[01]) ([1-5][0-9]{2}) [\x20-\x7e\x80-\xff]*", line)
        if not match:
            return Parsed(done=True, status="malformed")
        end = data.find(b"\r\n\r\n")
        header_complete = end != -1 and end + 4 <= 8192
        headers: list[tuple[str, str]] = []
        malformed = False
        for header in (
            rest.split(b"\r\n")[:-1] if end == -1 else data[len(line) + 2 : end].split(b"\r\n")
        ):
            if not header:
                continue
            name, colon, value = header.partition(b":")
            if (
                len(headers) >= 32
                or len(name) > 256
                or len(value) > 2048
                or not colon
                or not re.fullmatch(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name)
                or any(byte < 32 and byte != 9 or byte == 127 for byte in value)
            ):
                malformed = True
                break
            headers.append((name.decode("ascii"), value.strip(b" \t").decode("latin-1")))
        metadata = HttpMetadata(
            version="1.0" if match[1] == b"1.0" else "1.1",
            status=int(match[2]),
            headers=tuple(headers),
            headers_complete=header_complete and not malformed,
            body_offset=end + 4 if header_complete else None,
        )
        if malformed or (not header_complete and len(data) >= 8192):
            return Parsed(done=True, status="malformed", http=metadata)
        if not header_complete:
            return Parsed(done=eof, status="eof" if eof else "unknown", http=metadata)
        lengths = [value for name, value in headers if name.lower() == "content-length"]
        transfer = any(name.lower() == "transfer-encoding" for name, _ in headers)
        if lengths and (
            len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,20}", lengths[0]) or transfer
        ):
            return Parsed(done=True, status="malformed", http=metadata)
        no_body = metadata.status in (204, 304) or metadata.status < 200
        enough = no_body or (bool(lengths) and len(data) - end - 4 >= int(lengths[0]))
        return Parsed(
            done=enough or eof,
            http=metadata,
            status="complete" if enough or (eof and not lengths) else "eof" if eof else "unknown",
        )


class SshCollector:
    def accepts(self, data: bytes) -> bool:
        return data.startswith(b"SSH-") or b"\nSSH-" in data

    def inspect(self, data: bytes, *, eof: bool = False) -> Parsed:
        for index, line in enumerate(data.splitlines(keepends=True)):
            if index > 8:
                break
            if not line.startswith(b"SSH-"):
                continue
            if not line.endswith(b"\n"):
                return Parsed(done=eof or len(line) >= 255, status="malformed")
            match = re.fullmatch(
                rb"SSH-(2\.0|1\.99)-([\x21-\x2c\x2e-\x7e]+)(?: ([\x20-\x7e]*))?\r?\n", line
            )
            if not match or len(line) > 255:
                return Parsed(done=True, status="malformed")
            return Parsed(
                done=True,
                status="complete",
                ssh=SshMetadata(
                    protocol_version="2.0" if match[1] == b"2.0" else "1.99",
                    software=match[2].decode(),
                    comments=match[3].decode() if match[3] else None,
                ),
            )
        return Parsed(done=eof or len(data) >= 4096, status="malformed")


class SmtpCollector:
    def accepts(self, data: bytes) -> bool:
        return data.startswith(b"220")

    def inspect(self, data: bytes, *, eof: bool = False) -> Parsed:
        lines: list[str] = []
        for line in data.splitlines(keepends=True):
            if len(line) > 512 or len(lines) >= 32:
                return Parsed(done=True, status="malformed")
            if not line.endswith(b"\r\n"):
                return Parsed(done=eof, status="malformed")
            if not re.fullmatch(rb"220[ -][\x20-\x7e]+\r\n", line):
                return Parsed(done=True, status="malformed")
            lines.append(line[4:-2].decode())
            if line[3:4] == b" ":
                # 220 also belongs to FTP. Only an explicit SMTP token disambiguates.
                if any(
                    re.search(r"\bE?SMTP\b", text.partition(" ")[2], re.IGNORECASE)
                    for text in lines
                ):
                    return Parsed(
                        done=True, status="complete", smtp=SmtpMetadata(greeting=tuple(lines))
                    )
                return Parsed(
                    done=True, status="ambiguous", candidates=(Protocol.SMTP, Protocol.FTP)
                )
        return Parsed(done=eof, status="eof" if eof else "unknown")


COLLECTORS: tuple[Collector, ...] = (HttpCollector(), SshCollector(), SmtpCollector())


def inspect(data: bytes, *, eof: bool = False) -> Parsed:
    for collector in COLLECTORS:
        if collector.accepts(data):
            return collector.inspect(data, eof=eof)
    # Permit bounded SSH preambles and fragmented protocol prefixes. No active
    # request is ever sent after receiving even one byte of an unknown greeting.
    binary = any(byte < 32 and byte not in (9, 10, 13) or byte == 127 for byte in data)
    return Parsed(
        done=eof or binary or len(data) >= 4096, status="eof" if not data and eof else "unknown"
    )
