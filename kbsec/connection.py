from __future__ import annotations
import socket
import struct
import threading
import time
from typing import Optional

from .exceptions import KBConnectionError, KBTimeoutError

DEFAULT_HOST = '10.200.2.112'
DEFAULT_PORT = 8400
DEFAULT_TIMEOUT = 30


class DibConnection:
    """Single TCP socket connection to KB DIB server."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, timeout: int = DEFAULT_TIMEOUT):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()

    def connect(self) -> None:
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(self.timeout)
            self._sock.connect((self.host, self.port))
        except OSError as e:
            raise KBConnectionError(f'Connect failed: {e}') from e

    def disconnect(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def send_recv(self, payload: bytes) -> bytes:
        if not self._sock:
            raise KBConnectionError('Not connected')
        with self._lock:
            try:
                self._sock.sendall(payload)
                return self._recv_all()
            except socket.timeout as e:
                raise KBTimeoutError('Receive timed out') from e
            except OSError as e:
                raise KBConnectionError(f'Send/recv failed: {e}') from e

    def _recv_all(self) -> bytes:
        # DIB protocol: first 4 bytes = total length (big-endian)
        header = self._sock.recv(4)
        if len(header) < 4:
            raise KBConnectionError('Incomplete header')
        total_len = struct.unpack('>I', header)[0]
        data = b''
        while len(data) < total_len:
            chunk = self._sock.recv(total_len - len(data))
            if not chunk:
                raise KBConnectionError('Connection closed')
            data += chunk
        return header + data


class ConnectionPool:
    """Simple thread-safe connection pool (DibRootThread equivalent)."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, pool_size: int = 2, timeout: int = DEFAULT_TIMEOUT):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._pool: list[DibConnection] = []
        self._sem = threading.Semaphore(pool_size)
        self._lock = threading.Lock()
        for _ in range(pool_size):
            conn = DibConnection(host, port, timeout)
            conn.connect()
            self._pool.append(conn)

    def acquire(self) -> DibConnection:
        self._sem.acquire(timeout=self.timeout)
        with self._lock:
            return self._pool.pop()

    def release(self, conn: DibConnection) -> None:
        with self._lock:
            self._pool.append(conn)
        self._sem.release()

    def close_all(self) -> None:
        for conn in self._pool:
            conn.disconnect()
