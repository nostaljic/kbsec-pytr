# kbsec-pytr

Pure-Python KB Securities TR client — no JPype/JDK dependency.

## Install

```bash
pip install -e .
```

## Quick start

```python
from kbsec import KBSecClient, TrRuleManager
import os

# TR 룰 로드 (패키지 내 tr_rules/ 사용)
rule_dir = os.path.join(os.path.dirname(__file__), 'tr_rules')
client = KBSecClient(rule_dir=rule_dir)

# 현재가 조회 (GSS10030)
result = client.request('GSS10030', {'krxCd': 'NAS', 'isCd': 'AAPL'})
```

## Environments

| env | host | port |
|-----|------|------|
| dev | hts.kbsec.com | 5001 |
| prd | 128.12.248.170 | 5001 |
| external | 10.200.2.112 | 8400 |
