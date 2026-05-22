from __future__ import annotations
import struct
from typing import Dict, List

from .tr_rule import TrRule, FieldSpec

ENCODING = 'euc-kr'


def build_request(rule: TrRule, params: Dict[str, str], header_bytes: bytes) -> bytes:
    """Build DIB protocol request packet (PacketBinder equivalent)."""
    body_parts = []
    for fspec in rule.input_fields:
        value = str(params.get(fspec.name, ''))
        encoded = value.encode(ENCODING, errors='replace')
        # pad or truncate to field size
        if len(encoded) < fspec.size:
            encoded = encoded + b' ' * (fspec.size - len(encoded))
        else:
            encoded = encoded[:fspec.size]
        body_parts.append(encoded)
    body = b''.join(body_parts)
    # DIB frame: 4-byte big-endian length + header + body
    total = len(header_bytes) + len(body)
    return struct.pack('>I', total) + header_bytes + body


def parse_response(rule: TrRule, raw: bytes) -> Dict[str, str]:
    """Parse DIB protocol response packet into field dict."""
    # skip 4-byte length prefix + 61-byte response header
    HEADER_OFFSET = 4 + 61
    body = raw[HEADER_OFFSET:]
    offset = 0
    result: Dict[str, str] = {}
    for fspec in rule.output_fields:
        chunk = body[offset:offset + fspec.size]
        result[fspec.name] = chunk.decode(ENCODING, errors='replace').strip()
        offset += fspec.size
    return result
