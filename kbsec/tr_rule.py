from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List
from xml.etree import ElementTree as ET


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


class TrRuleManager:
    _rules: Dict[str, TrRule] = {}

    @classmethod
    def load(cls, rule_dir: str) -> None:
        for xml_file in Path(rule_dir).glob('*.xml'):
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                tr_code = root.findtext('TrCode') or xml_file.stem
                rule = TrRule(tr_code=tr_code)
                for f in root.findall('.//Input/Field'):
                    rule.input_fields.append(FieldSpec(
                        name=f.findtext('Name') or '',
                        size=int(f.findtext('Size') or 0),
                        type=f.findtext('Type') or 'A',
                        desc=f.findtext('Desc') or '',
                    ))
                for f in root.findall('.//Output/Field'):
                    rule.output_fields.append(FieldSpec(
                        name=f.findtext('Name') or '',
                        size=int(f.findtext('Size') or 0),
                        type=f.findtext('Type') or 'A',
                        desc=f.findtext('Desc') or '',
                    ))
                cls._rules[tr_code] = rule
            except Exception:
                pass

    @classmethod
    def get(cls, tr_code: str) -> TrRule:
        if tr_code not in cls._rules:
            raise KeyError(f'TR rule not found: {tr_code}')
        return cls._rules[tr_code]
