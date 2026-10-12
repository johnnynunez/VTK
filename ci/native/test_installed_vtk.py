"""Fresh native environment: every packaged extension and DLL must load."""
import ctypes
import importlib
import importlib.metadata
import json
from pathlib import Path
import sys
import sysconfig

assert sysconfig.get_platform() == 'win-arm64' and sys.version_info[:2] == (3, 12)
import vtk
assert vtk.vtkVersion.GetVTKVersion() == '9.6.2'
dist = importlib.metadata.distribution('vtk')
loaded = []
for f in dist.files:
    if str(f).lower().endswith('.pyd'):
        module = '.'.join(Path(str(f)).parts).split('.cp312-')[0]
        importlib.import_module(module)
        loaded.append(str(f))
assert len(loaded) == 125, len(loaded)
for f in dist.files:
    if str(f).lower().endswith('.dll'):
        ctypes.WinDLL(str(dist.locate_file(f).resolve()))
        loaded.append(str(f))
assert len(loaded) > 125
Path(sys.argv[1]).write_text(json.dumps({'platform': sysconfig.get_platform(), 'version': vtk.vtkVersion.GetVTKVersion(), 'loaded': loaded, 'gpu_claim': False}, indent=2))
print('All packaged extensions and DLLs loaded:', len(loaded))
