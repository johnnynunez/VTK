"""Attach exact public source provenance and unmodified dependency notices."""
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

SOURCE = 'f49a1dbafa60b58ef22f6292ec58370453162192'


def bundle(wheel, source, out):
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == SOURCE
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=source).decode().split('\0')
    archive = out/'vtk-9.6.2-public-source.tar.gz'
    subprocess.run(['git', 'archive', '--format=tar.gz', '--prefix=vtk-9.6.2/', '-o', str(archive), SOURCE], cwd=source, check=True)
    provenance = {'source_sha': SOURCE, 'source_url': 'https://gitlab.kitware.com/vtk/vtk/-/tree/'+SOURCE,
                  'source_archive': archive.name, 'source_archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                  'scope': 'Exact unmodified public VTK source including vendored third-party sources and license choices; not a blanket legal compliance opinion'}
    additions = {}
    notices = []
    for name in tracked:
        if not name: continue
        p = source/name
        if p.is_file() and (any(s in p.name.upper() for s in ('LICENSE', 'COPYING', 'COPYRIGHT', 'NOTICE')) or p.name == 'vtk.module'):
            data = p.read_bytes()
            dest = 'vtk-9.6.2.dist-info/licenses/source/'+name
            additions[dest] = data
            notices.append({'path': name, 'sha256': hashlib.sha256(data).hexdigest(), 'copyleft_text_present': any(s in data.lower() for s in (b'general public license', b'mozilla public license'))})
    provenance['notices'] = notices
    text = json.dumps(provenance, indent=2).encode()
    additions['vtk-9.6.2.dist-info/source-provenance.json'] = text
    (out/'source-license-provenance.json').write_bytes(text)
    record_name = 'vtk-9.6.2.dist-info/RECORD'
    temporary = wheel.with_suffix('.tmp')
    rows = []
    with zipfile.ZipFile(wheel) as old, zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as new:
        for name in old.namelist():
            if name == record_name: continue
            assert name not in additions
            data = old.read(name)
            new.writestr(name, data)
            rows.append((name, 'sha256='+base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('='), len(data)))
        for name, data in additions.items():
            new.writestr(name, data)
            rows.append((name, 'sha256='+base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('='), len(data)))
        rows.append((record_name, '', ''))
        record = io.StringIO(); csv.writer(record).writerows(rows)
        new.writestr(record_name, record.getvalue())
    temporary.replace(wheel)
    print('Preserved public source and notices:', len(notices))


if __name__ == '__main__':
    bundle(*(Path(x).resolve() for x in sys.argv[1:]))
