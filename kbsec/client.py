from __future__ import annotations
import xml.etree.ElementTree as ET
from typing import Dict, Optional

from .connection import ConnectionPool
from .header import RequestHeader
from .packet import build_request, parse_response
from .tr_rule import TrRuleManager
from .exceptions import KBSecConfigError, KBSecConnectionError, KBSecRequestError


class KBSecClient:
    """Pure-Python replacement for JKASSClient (no JPype/JDK required)."""

    def __init__(
        self,
        host: str = 'hts.kbsec.com',
        port: int = 5001,
        pool_size: int = 2,
        timeout: int = 30,
        rule_dir: str = None,
    ) -> None:
        self._pool = ConnectionPool(
            host=host, port=port, pool_size=pool_size, timeout=timeout
        )
        if rule_dir:
            TrRuleManager.load(rule_dir)

    @classmethod
    def from_config(cls, config_path: str) -> 'KBSecClient':
        """Load from KASSConf.xml (reverse-engineered config format)."""
        try:
            tree = ET.parse(config_path)
            root = tree.getroot()
            host = root.findtext('.//ServerIP') or 'hts.kbsec.com'
            port = int(root.findtext('.//ServerPort') or 5001)
            pool_size = int(root.findtext('.//NodeCount') or 2)
            timeout = int(root.findtext('.//RqTimeout') or 30)
            rule_dir = root.findtext('.//TrRuleDir')
        except Exception as e:
            raise KBSecConfigError(f'Failed to parse config: {e}') from e
        return cls(host=host, port=port, pool_size=pool_size, timeout=timeout, rule_dir=rule_dir)

    def request(
        self,
        tr_code: str,
        params: Dict[str, str],
        user_id: str = '',
        account_no: str = '',
    ) -> Dict[str, str]:
        """Execute a TR request and return parsed response fields."""
        rule = TrRuleManager.get(tr_code)
        header = RequestHeader(tr_code=tr_code, user_id=user_id, account_no=account_no)
        payload = build_request(rule, params, header.encode())
        conn = self._pool.acquire()
        try:
            raw = conn.send_recv(payload)
        except Exception as e:
            raise KBSecRequestError(f'TR {tr_code} failed: {e}') from e
        finally:
            self._pool.release(conn)
        return parse_response(rule, raw)

    def close(self) -> None:
        self._pool.close_all()

    def __enter__(self) -> 'KBSecClient':
        return self

    def __exit__(self, *_) -> None:
        self.close()
