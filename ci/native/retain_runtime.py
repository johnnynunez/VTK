"""Always-run archive of public build DLLs, symbols and import libraries."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile


def retain(build, out):
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    with zipfile.ZipFile(out/'build-runtime-symbols.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        for p in sorted(build.rglob('*')):
            if not p.is_file() or p.suffix.lower() not in {'.dll', '.pyd', '.exe', '.pdb', '.lib', '.exp'}:
                continue
            data = p.read_bytes()
            row = {'path': p.relative_to(build).as_posix(), 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            if data.startswith(b'MZ'):
                offset = struct.unpack_from('<I', data, 0x3c)[0]
                row['machine'] = hex(struct.unpack_from('<H', data, offset + 4)[0])
            z.writestr(row['path'], data)
            rows.append(row)
    (out/'runtime-manifest.json').write_text(json.dumps(rows, indent=2))
    print('Retained runtime/symbol/import-library files:', len(rows))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('build', type=Path)
    p.add_argument('out', type=Path)
    a = p.parse_args()
    retain(a.build, a.out)
