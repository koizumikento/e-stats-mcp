"""Bounded regression for dnspython's compressed-name traversal limit."""

import struct

import dns.message
import dns.name
import pytest


def compression_chain(hops: int) -> tuple[bytes, int]:
    wire = b"\x00\x00"
    for hop in range(hops):
        wire += struct.pack("!H", 0xC000 | (hop * 2))
    return wire, len(wire) - 2 if hops else 0


@pytest.mark.parametrize("hops", [0, 1, 16])
def test_compression_within_limit(hops):
    wire, start = compression_chain(hops)
    name, consumed = dns.name.from_wire(wire, start)
    assert name == dns.name.root
    assert consumed == (2 if hops else 1)


def test_compression_chain_rejects_seventeenth_pointer():
    wire, start = compression_chain(17)
    with pytest.raises(dns.name.PointerChainTooLong):
        dns.name.from_wire(wire, start)


def test_ordinary_dns_message_round_trip():
    query = dns.message.make_query("synthetic.example.", "MX")
    assert dns.message.from_wire(query.to_wire()).question == query.question
