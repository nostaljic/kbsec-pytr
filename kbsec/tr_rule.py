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
        """Load TR rule XMLs from directory.

        XML structure: <Name>TR_CODE</Name>
        Input fields:  <I Name="..." Size="..." format="..." Desc="..." />
        Output fields: <O Name="..." Size="..." format="..." Desc="..." />
        """
        for xml_file in Path(rule_dir).glob('*.xml'):
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                # <Name>GSS10030</Name>
                tr_code = root.findtext('Name') or xml_file.stem
                rule = TrRule(tr_code=tr_code)
                # Input fields use <I Name="..." Size="..." /> attributes
                for f in root.findall('.//Input/I'):
                    name = f.get('Name') or ''
                    size_str = f.get('Size') or '0'
                    rule.input_fields.append(FieldSpec(
                        name=name,
                        size=int(size_str),
                        type=f.get('format') or 'A',
                        desc=f.get('Desc') or '',
                    ))
                # Output fields use <O Name="..." Size="..." /> attributes
                for f in root.findall('.//Output/O'):
                    name = f.get('Name') or ''
                    size_str = f.get('Size') or '0'
                    rule.output_fields.append(FieldSpec(
                        name=name,
                        size=int(size_str),
                        type=f.get('format') or 'A',
                        desc=f.get('Desc') or '',
                    ))
                cls._rules[tr_code] = rule
            except Exception:
                pass

    @classmethod
    def get(cls, tr_code: str) -> TrRule:
        if tr_code not in cls._rules:
            raise KeyError(f'TR rule not found: {tr_code}')
        return cls._rules[tr_code]
