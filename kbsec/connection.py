"""
KB증권 DIB 프로토콜 순수 Python 구현
doHandShakeNewWay 시퀀스: AUTH01 수신 → V/X → InitNodeMGL → V/O+LOGIN_DATA
"""
import socket
import struct
import time
import os

# ── 헤더 상수 ──────────────────────────────────────────────────────────────
HCOMM_LEN     = 30   # hcomm_header: data_length(5)+func_cd(1)+tr_info(6)+MGL(6)+media_gb(3)+cipher_comp(1)+public_cert(1)+filler(7) = 30 (JAR CFR 실측)
HCOMM_NEW_LEN = 10   # hcomm_header_new 길이 (POSITION 1 + CON_SEQ 2 + SUB_FUNC 1 + RQ_ID 2 + RESULT 1 + filler 3)

DEFAULT_HOST  = "hts.kbsec.com"
DEFAULT_PORT  = 5001
TIMEOUT       = 15.0


def _pad_right(s: str, length: int, ch: str = ' ') -> bytes:
    return s[:length].ljust(length, ch).encode('ascii')


def _pad_left_zero(s: str, length: int) -> bytes:
    return s.zfill(length)[:length].encode('ascii')


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _build_login_data() -> bytes:
    """LOGIN_DATA.getBytes() — 69 bytes"""
    hostname = socket.gethostname()
    name_tag = f"WAS_{hostname}"
    user_id       = _pad_right(name_tag, 12)          # 12
    public_ip     = _pad_right(_get_local_ip(), 15)   # 15
    media         = _pad_right("404", 3)              # 3
    mac_addr      = _pad_right("MAC_000000000000", 18)# 18
    brno          = _pad_right("000", 3)              # 3
    csno          = _pad_right(name_tag.ljust(16,'0')[:16], 16)  # 16
    real_compress = _pad_right(" ", 1)                # 1
    real_level    = _pad_right("B", 1)                # 1
    return user_id + public_ip + media + mac_addr + brno + csno + real_compress + real_level


def _build_new_comm_header(func_cd: int, sub_func: int, mgl: bytes, body_len: int, req_id: int = 1, tr_code: str = "") -> bytes:
    """
    KB NewComm 헤더 빌드 (JAR CFR 실측 기준)
    HCommHeader (30 bytes) + HCommHeader_NEW (10 bytes) = 40 bytes total
    HCommHeader: data_length(5)+func_cd(1)+tr_info(6)+MGL(6)+media_gb(3)+cipher_comp(1)+public_cert(1)+filler(7) = 30
    HCommHeader_NEW: POSITION(1)+CON_SEQ(2)+SUB_FUNC(1)+RQ_ID(2)+RESULT(1)+filler(3) = 10
    data_length = 30 + 10 + body_len - 5 = 35 + body_len
    """
    total_data = 30 + 10 + body_len - 5  # = 35 + body_len
    data_length = str(total_data).zfill(5).encode('ascii')  # 5 bytes

    hcomm = bytearray(30)
    hcomm[0:5]   = data_length                              # data_length  5
    hcomm[5]     = func_cd                                  # func_cd      1
    hcomm[6:12]  = _pad_right(tr_code, 6)                   # tr_info      6
    if mgl and len(mgl) >= 6:
        hcomm[12:18] = mgl[:6]                              # MGL          6
    else:
        hcomm[12:18] = b'\x00' * 6
    hcomm[18:21] = b'404'                                   # media_gb     3
    hcomm[21]    = ord(' ')                                 # cipher_comp  1
    hcomm[22]    = ord(' ')                                 # public_cert  1
    hcomm[23:30] = b' ' * 7                                 # filler       7

    hcomm_new = bytearray(10)
    hcomm_new[0]   = 0x4F                                   # POSITION = 'O'
    hcomm_new[1:3] = b'  '                                  # CON_SEQ  2
    hcomm_new[3]   = sub_func                               # SUB_FUNC 1
    hcomm_new[4:6] = struct.pack('>H', req_id)              # RQ_ID    2
    hcomm_new[6]   = ord(' ')                               # RESULT   1
    hcomm_new[7:10]= b'   '                                 # filler   3

    return bytes(hcomm) + bytes(hcomm_new)


class KBConnection:
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self._sock: socket.socket | None = None
        self._mgl: bytes = b'\x00' * 6
        self._global_id: bytes = b'\x00' * 4
        self._req_id: int = 1

    def connect(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(TIMEOUT)
        self._sock.connect((self.host, self.port))

    def close(self):
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def _recv_exact(self, n: int) -> bytes:
        buf = b''
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("Connection closed by server")
            buf += chunk
        return buf

    def _recv_response(self) -> bytes:
        """
        KB 프로토콜: 첫 5바이트 = data_length (ASCII 숫자)
        total_len = int(data_length) + 5
        """
        header5 = self._recv_exact(5)
        try:
            data_len = int(header5.decode('ascii').strip())
        except ValueError:
            # 바이너리 응답 fallback: 남은 데이터 읽기
            rest = b''
            try:
                self._sock.settimeout(2.0)
                while True:
                    chunk = self._sock.recv(4096)
                    if not chunk:
                        break
                    rest += chunk
            except socket.timeout:
                pass
            self._sock.settimeout(TIMEOUT)
            return header5 + rest
        rest = self._recv_exact(data_len)
        return header5 + rest

    def _init_node_mgl(self, rp_session_key: bytes):
        """InitNodeMGL: rpSessionkey[6:12] → MGL(6bytes), [6:10] → GlobalID(4bytes)"""
        if rp_session_key and len(rp_session_key) >= 12:
            self._mgl = rp_session_key[6:12]
            self._global_id = rp_session_key[6:10]

    def perform_handshake(self) -> bool:
        """
        doHandShakeNewWay 시퀀스:
        1. 서버 AUTH01 push 수신 (TCP 연결 직후)
        2. V/X 패킷 송신 → rpSessionkey 수신
        3. InitNodeMGL
        4. V/O + LOGIN_DATA 송신 → rpLoginData 수신
        """
        # Step 1: 서버 AUTH01 push 수신
        auth01 = self._recv_response()
        print(f"[HANDSHAKE] AUTH01 received: {auth01!r}")

        # Step 2: RequestSessionKey — V/X, body 없음
        self._req_id = 1
        header_vx = _build_new_comm_header(
            func_cd=0x56, sub_func=0x58,
            mgl=self._mgl, body_len=0, req_id=self._req_id
        )
        self._sock.sendall(header_vx)
        rp_session_key = self._recv_response()
        print(f"[HANDSHAKE] rpSessionkey received ({len(rp_session_key)} bytes): {rp_session_key!r}")

        # Step 3: InitNodeMGL
        self._init_node_mgl(rp_session_key)
        print(f"[HANDSHAKE] MGL={self._mgl.hex()}, GlobalID={self._global_id.hex()}")

        # Step 4: sendLoginData_NEW — V/O + LOGIN_DATA
        self._req_id = 2
        login_data = _build_login_data()
        header_vo = _build_new_comm_header(
            func_cd=0x56, sub_func=0x4F,
            mgl=self._mgl, body_len=len(login_data), req_id=self._req_id
        )
        self._sock.sendall(header_vo + login_data)
        rp_login_data = self._recv_response()
        # JAR doHandShakeNewWay: rpLoginData는 null 체크만 — 내용 파싱 없음
        return rp_login_data is not None

    def send_tr(self, tr_code: str, body: bytes = b'') -> bytes:
        """핸드셰이크 완료 후 일반 TR 송신"""
        self._req_id += 1
        header = _build_new_comm_header(
            func_cd=0x56, sub_func=0x45,  # 'E' — 일반 TR
            mgl=self._mgl, body_len=len(body), req_id=self._req_id
        )
        self._sock.sendall(header + body)
        return self._recv_response()


def test_handshake(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    conn = KBConnection(host, port)
    try:
        print(f"[TEST] Connecting to {host}:{port}...")
        conn.connect()
        print("[TEST] TCP_CONNECT_OK")
        result = conn.perform_handshake()
        print(f"[TEST] HANDSHAKE_OK: {result}")
        return result
    except Exception as e:
        print(f"[TEST] ERROR: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    test_handshake()


class ConnectionPool:
    """
    KBConnection 기반 ConnectionPool 래퍼.
    client.py 인터페이스(acquire/release/close_all) 호환.
    """
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                 pool_size: int = 2, timeout: int = 30):
        self.host = host
        self.port = port
        self.pool_size = pool_size
        self.timeout = float(timeout)
        self._conns: list[KBConnection] = []

    def acquire(self) -> KBConnection:
        """연결 풀에서 연결 획득 (없으면 신규 생성 + 핸드셰이크)"""
        if self._conns:
            return self._conns.pop()
        conn = KBConnection(self.host, self.port)
        conn._sock and None  # type hint
        conn.connect()
        conn.perform_handshake()
        return conn

    def release(self, conn: KBConnection):
        """연결 반환 (pool_size 초과 시 닫음)"""
        if len(self._conns) < self.pool_size:
            self._conns.append(conn)
        else:
            conn.close()

    def close_all(self):
        for conn in self._conns:
            conn.close()
        self._conns.clear()

    def send_recv(self, payload: bytes) -> bytes:
        """단일 요청용 편의 메서드 (acquire → send_recv → release)"""
        conn = self.acquire()
        try:
            conn._sock.sendall(payload)
            return conn._recv_response()
        finally:
            self.release(conn)
