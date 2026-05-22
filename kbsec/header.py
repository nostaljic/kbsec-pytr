from __future__ import annotations
import time
from dataclasses import dataclass, field

CHANNEL_ID = '34W'
HEADER_SIZE = 500
WORK_TYPE_REQ = '1'
CONNECT_SERVER_VERSION = 'NEWKASS'
GIANT_MSG_VERSION = '134'


@dataclass
class RequestHeader:
    '''DIB NEWKASS protocol request header (HeaderWrap equivalent).

    Fixed 500-byte header matching KASSConf.xml spec:
      tr_code(10) + body_len(8) + user_id(20) + account_no(20) +
      channel_id(4) + work_type(1) + seq_no(6) + jitum_code(3) +
      buso(3) + sabun(6) + screen_id(5) + giant_msg_version(3) +
      connect_server_version(10) + reserved(pad to 500)
    '''
    tr_code: str
    user_id: str
    body_len: int = 0
    account_no: str = ''
    channel_id: str = CHANNEL_ID
    work_type: str = WORK_TYPE_REQ
    seq_no: str = field(default_factory=lambda: str(int(time.time() * 1000) % 1000000))
    jitum_code: str = '100'
    buso: str = '100'
    sabun: str = '000000'
    screen_id: str = '00000'
    giant_msg_version: str = GIANT_MSG_VERSION
    connect_server_version: str = CONNECT_SERVER_VERSION

    def encode(self) -> bytes:
        '''Encode header to EUC-KR fixed 500-byte buffer.'''
        parts = (
            self.tr_code.ljust(10)[:10]
            + str(self.body_len).rjust(8)[:8]
            + self.user_id.ljust(20)[:20]
            + self.account_no.ljust(20)[:20]
            + self.channel_id.ljust(4)[:4]
            + self.work_type.ljust(1)[:1]
            + self.seq_no.ljust(6)[:6]
            + self.jitum_code.ljust(3)[:3]
            + self.buso.ljust(3)[:3]
            + self.sabun.ljust(6)[:6]
            + self.screen_id.ljust(5)[:5]
            + self.giant_msg_version.ljust(3)[:3]
            + self.connect_server_version.ljust(10)[:10]
        )
        parts = parts.ljust(HEADER_SIZE)[:HEADER_SIZE]
        return parts.encode('euc-kr', errors='replace')

    @staticmethod
    def decode(data: bytes) -> dict:
        text = data.decode('euc-kr', errors='replace')
        return {
            'tr_code':                  text[0:10].strip(),
            'body_len':                  text[10:18].strip(),
            'user_id':                   text[18:38].strip(),
            'account_no':                 text[38:58].strip(),
            'channel_id':                 text[58:62].strip(),
            'work_type':                  text[62:63].strip(),
            'seq_no':                     text[63:69].strip(),
            'jitum_code':                 text[69:72].strip(),
            'buso':                       text[72:75].strip(),
            'sabun':                      text[75:81].strip(),
            'screen_id':                  text[81:86].strip(),
            'giant_msg_version':          text[86:89].strip(),
            'connect_server_version':     text[89:99].strip(),
        }
