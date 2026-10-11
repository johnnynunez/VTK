"""Static wheel RECORD, tag, hash, PE machine and import inventory."""
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import zipfile


def audit(path):
    result = {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "native": []}
    with zipfile.ZipFile(path) as z:
        records = [n for n in z.namelist() if n.endswith('.dist-info/RECORD')]
        assert len(records) == 1
        rows = list(csv.reader(io.StringIO(z.read(records[0]).decode())))
        for name, digest, size in rows:
            data = z.read(name)
            if digest:
                algorithm, expected = digest.split('=', 1)
                actual = base64.urlsafe_b64encode(hashlib.new(algorithm, data).digest()).decode().rstrip('=')
                assert actual == expected, ('RECORD', name)
                assert len(data) == int(size), ('size', name)
        assert {r[0] for r in rows} == {n for n in z.namelist() if not n.endswith('/')}
        result['record_entries'] = len(rows)
        for name in z.namelist():
            if name.lower().endswith(('.pyd', '.dll', '.exe')):
                data = z.read(name)
                assert data[:2] == b'MZ'
                offset = struct.unpack_from('<I', data, 0x3c)[0]
                assert data[offset:offset+4] == b'PE\0\0'
                machine = struct.unpack_from('<H', data, offset+4)[0]
                entry = {'path': name, 'machine': hex(machine), 'sha256': hashlib.sha256(data).hexdigest()}
                try:
                    import pefile
                    pe = pefile.PE(data=data)
                    entry['imports'] = [e.dll.decode() for e in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', [])]
                except ImportError:
                    pass
                result['native'].append(entry)
        result['all_native_arm64'] = bool(result['native']) and all(n['machine'] == '0xaa64' for n in result['native'])
        result['wheel_metadata'] = z.read(next(n for n in z.namelist() if n.endswith('.dist-info/WHEEL'))).decode()
    return result

if __name__ == '__main__':
    report = [audit(p) for p in Path(sys.argv[1]).glob('*.whl')]
    Path(sys.argv[2]).write_text(json.dumps(report, indent=2))
    assert report and all(r['all_native_arm64'] for r in report), 'Non-ARM64 native wheel payload: inspect report'
    print(json.dumps(report, indent=2))
