"""Operator-only public behavior programs; never inserted in fresh solver inputs."""

from __future__ import annotations

import json
import re

from patchloop.util import sha256_bytes

PYDICOM_WRITE = r'''
import io, json
from pydicom import dcmread
from pydicom.dataset import Dataset
rows = []
for name, vr, value in [('repair', 'OL', bytes(range(1,101))),
                        ('ordinary', 'OL', bytes(range(1,11))),
                        ('preserve', 'OB', bytes(range(1,101)))]:
    ds = Dataset(); ds.is_little_endian = True; ds.is_implicit_VR = False
    ds.add_new(0x00660040, vr, value)
    row = {'case': name, 'contains_backslash': 92 in value,
           'constructed_type': type(ds[0x00660040].value).__name__}
    try:
        stream = io.BytesIO(); ds.save_as(stream); stream.seek(0)
        actual = dcmread(stream, force=True)[0x00660040].value
        row.update(saved=True, bytes_preserved=isinstance(actual, bytes) and actual == value)
    except Exception as exc:
        row.update(saved=False, error=type(exc).__name__)
    rows.append(row)
print(json.dumps(rows))
'''

PYDICOM_JSON = r'''
import json
from pydicom import config
from pydicom.dataset import Dataset
from pydicom.dataelem import RawDataElement
from pydicom.tag import Tag
tag = Tag(0x00200013)
config.settings.reading_validation_mode = config.RAISE
rows = []
for suppress in [True, False]:
    ds = Dataset(); ds.PatientName = 'Example^Patient'
    ds[tag] = RawDataElement(tag, 'IS', 4, b'2.0 ', 0, True, True)
    row = {'suppress': suppress, 'raw_before': isinstance(ds._dict[tag], RawDataElement),
           'raw_value': ds._dict[tag].value.decode('ascii')}
    try:
        ds[tag]
        row['conversion_rejected'] = False
    except (TypeError, ValueError):
        row['conversion_rejected'] = True
    ds[tag] = RawDataElement(tag, 'IS', 4, b'2.0 ', 0, True, True)
    try:
        result = ds.to_json_dict(suppress_invalid_tags=suppress)
        row.update(completed=True, invalid_omitted='00200013' not in result,
                   valid_preserved=result.get('00100010', {}).get('Value') ==
                   [{'Alphabetic': 'Example^Patient'}])
    except Exception as exc:
        row.update(completed=False, error=type(exc).__name__)
    rows.append(row)
print(json.dumps(rows))
'''


def design(case: str, issue: str) -> dict:
    issue = issue.replace('\r', '')
    expected = None
    if case == '1733':
        before, after = issue.split('## Expected Behaviour', 1)
        def block(s):
            return re.findall(r'```sql\s*\n(.*?)```', s, re.S)
        initial = block(before)[0]
        expected = block(after.split('## Observed Behaviour', 1)[0])[0].splitlines()
        source = ("import json\nfrom sqlfluff.core import Linter\n"
                  f"result=Linter(dialect='ansi').lint_string({initial!r},fix=True)\n"
                  "print(json.dumps({'output':result.fix_string()[0]}))\n")
    elif case == '1413':
        source = PYDICOM_WRITE
    elif case == '1694':
        source = PYDICOM_JSON
    else:
        raise ValueError('unknown public case')
    return {'case': case, 'program': source, 'expected_lines': expected,
            'program_hash': sha256_bytes(source.encode()),
            'issue_hash': sha256_bytes(issue.encode())}


def classify(result: dict, spec: dict) -> dict:
    if result.get('exit_code') != 0 or any(result.get(k) for k in (
        'timed_out', 'cleanup_failed', 'truncated', 'deadline_exhausted',
    )):
        return {'status': 'UNASSESSED', 'reason': 'execution'}
    try:
        rows = json.loads(result['stdout'])
        if spec['case'] == '1733':
            valid = isinstance(rows, dict) and isinstance(rows.get('output'), str)
            passed = valid and rows['output'].splitlines() == spec['expected_lines']
        elif spec['case'] == '1413':
            valid = (isinstance(rows, list) and len(rows) == 3
                     and [r['case'] for r in rows] == ['repair', 'ordinary', 'preserve']
                     and [r['contains_backslash'] for r in rows] == [True, False, True])
            passed = valid and all(r.get('saved') is True and r.get('bytes_preserved') is True
                                   for r in rows)
        else:
            valid = (isinstance(rows, list) and len(rows) == 2
                     and [r['suppress'] for r in rows] == [True, False]
                     and all(r['raw_before'] is True and r['raw_value'] == '2.0 '
                             and r['conversion_rejected'] is True for r in rows))
            passed = (valid and rows[0].get('completed') is True
                      and rows[0].get('invalid_omitted') is True
                      and rows[0].get('valid_preserved') is True
                      and rows[1].get('completed') is False
                      and rows[1].get('error') in {'TypeError', 'ValueError'})
        return {'status': ('PASS' if passed else 'FAIL') if valid else 'UNASSESSED',
                'observed': rows, 'scope': 'operator public examples; not complete task coverage'}
    except (ValueError, KeyError, TypeError, AttributeError):
        return {'status': 'UNASSESSED', 'reason': 'invalid observation'}
