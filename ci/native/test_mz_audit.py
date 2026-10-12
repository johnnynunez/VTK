import base64
import csv
import io
from pathlib import Path
import zipfile
import hashlib
import os
from wheel_audit import audit


def test_all_mz_not_just_dll_suffix(tmp_path):
    original = Path(os.environ['ORIGINAL_VTK_WHEEL'])
    with zipfile.ZipFile(original) as z:
        data = z.read('vtkmodules/vtkCommonColor.cp312-win_arm64.pyd')
    entries = {'payload.bin': data, 'vtk-9.6.2.dist-info/WHEEL': b'Tag: cp312-cp312-win_arm64\n'}
    record = io.StringIO()
    w = csv.writer(record)
    for name, content in entries.items():
        w.writerow((name, 'sha256='+base64.urlsafe_b64encode(hashlib.sha256(content).digest()).decode().rstrip('='), len(content)))
    w.writerow(('vtk-9.6.2.dist-info/RECORD', '', ''))
    wheel = tmp_path/'vtk-9.6.2-cp312-cp312-win_arm64.whl'
    with zipfile.ZipFile(wheel, 'w') as z:
        for n, d in entries.items(): z.writestr(n, d)
        z.writestr('vtk-9.6.2.dist-info/RECORD', record.getvalue())
    report = audit(wheel)
    assert [r['path'] for r in report['native']] == ['payload.bin']
