from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List
import re


@dataclass
class FieldSpec:
    name: str
    size: int
    type: str = 'A'
    desc: str = ''


@dataclass
class TrRule:
    tr_code: str
    input_fields: List[FieldSpec] = field(default_factory=list)
    output_fields: List[FieldSpec] = field(default_factory=list)


def _parse_fields_regex(block: str, tag: str) -> List[FieldSpec]:
    fields = []
    attr_pat = re.compile(r'(\w+)="([^"]*)"')
    for m in re.finditer(r'<' + tag + r'\s+([^>]+?)\s*/?>', block, re.DOTALL):
        attrs = dict(attr_pat.findall(m.group(1)))
        name = attrs.get('Name', '')
        try:
            size = int(attrs.get('Size', '0'))
        except ValueError:
            size = 0
        fields.append(FieldSpec(
            name=name,
            size=size,
            type=attrs.get('format', 'A'),
            desc='',
        ))
    return fields


class TrRuleManager:
    _rules: Dict[str, TrRule] = {}

    @classmethod
    def load(cls, rule_dir: str) -> None:
        """Load TR rule XMLs (EUC-KR encoded) from directory."""
        for xml_file in Path(rule_dir).glob('*.xml'):
            try:
                raw = xml_file.read_bytes()
                text = raw.decode('euc-kr', errors='replace')
                m = re.search(r'<Name>([^<]+)</Name>', text)
                tr_code = m.group(1).strip() if m else xml_file.stem
                rule = TrRule(tr_code=tr_code)
                in_m = re.search(r'<Input[^>]*>(.*?)</Input>', text, re.DOTALL)
                if in_m:
                    rule.input_fields = _parse_fields_regex(in_m.group(1), 'I')
                out_m = re.search(r'<Output[^>]*>(.*?)</Output>', text, re.DOTALL)
                if out_m:
                    rule.output_fields = _parse_fields_regex(out_m.group(1), 'O')
                cls._rules[tr_code] = rule
            except Exception:
                pass

    @classmethod
    def get(cls, tr_code: str) -> TrRule:
        if tr_code not in cls._rules:
            raise KeyError(f'TR rule not found: {tr_code}')
        return cls._rules[tr_code]
