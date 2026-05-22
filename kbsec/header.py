from __future__ import annotations
import struct
import time
from dataclasses import dataclass, field


CHANNEL_ID = '34W'
HEADER_SIZE = 500
WORK_TYPE_REQ = '1'


@dataclass
class RequestHeader:
    """DIB protocol request header (HeaderWrap equivalent)."""
    tr_code: str
    user_id: str
    account_no: str = ''
    channel_id: str = CHANNEL_ID
    work_type: str = WORK_TYPE_REQ
    seq_no: str = field(default_factory=lambda: str(int(time.time() * 1000) % 1000000))

    def encode(self) -> bytes:
        """Encode header to EUC-KR fixed-length bytes."""
        buf = (
            self.tr_code.ljust(10)[:10]
            + self.user_id.ljust(20)[:20]
            + self.account_no.ljust(20)[:20]
            + self.channel_id.ljust(4)[:4]
            + self.work_type.ljust(1)[:1]
            + self.seq_no.ljust(6)[:6]
        )
        return buf.encode('euc-kr', errors='replace')

    @staticmethod
    def decode(data: bytes) -> dict:
        text = data.decode('euc-kr', errors='replace')
        return {
            'tr_code': text[:10].strip(),
            'user_id': text[10:30].strip(),
            'account_no': text[30:50].strip(),
            'channel_id': text[50:54].strip(),
            'work_type': text[54],
            'seq_no': text[55:61].strip(),
        }
