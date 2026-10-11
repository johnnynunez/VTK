"""Hosted-only VTK wheel build from authoritative GitLab source."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import sysconfig
import urllib.request

assert sys.platform == 'win32' and sysconfig.get_platform() == 'win-arm64'
root = Path(os.environ['GITHUB_WORKSPACE'])
out = root/'evidence'; out.mkdir(exist_ok=True)
work = Path(os.environ['RUNNER_TEMP'])/'geometry-vtk';work.mkdir(exist_ok=True)
source = work/'source';build = work/'build'
for key in ('PIP_CACHE_DIR','NUGET_PACKAGES','NUGET_HTTP_CACHE_PATH','NUGET_PLUGINS_CACHE_PATH','VIRTUALENV_OVERRIDE_APP_DATA','UV_CACHE_DIR','UV_PYTHON_INSTALL_DIR','UV_PYTHON_BIN_DIR'):
    os.environ[key] = str(work/key)
log = (out/'commands.log').open('a',encoding='utf-8')

def run(args,cwd=work):
    print('RUN',args,flush=True);log.write('RUN '+repr(args)+'\n');log.flush()
    proc = subprocess.Popen([str(x) for x in args],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
    for line in proc.stdout:
        print(line,end='',flush=True);log.write(line);log.flush()
    code = proc.wait()
    if code:
        raise subprocess.CalledProcessError(code,args)

run(['git','clone','--depth','1','--branch','v9.6.2','https://gitlab.kitware.com/vtk/vtk.git',source])
sha = subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
assert sha == 'f49a1dbafa60b58ef22f6292ec58370453162192'
(out/'provenance.json').write_text(json.dumps({'upstream':'https://gitlab.kitware.com/vtk/vtk','source_sha':sha,'python':sys.version,'platform':platform.platform(),'gpu':False,'rendering_backend_built':'Win32 OpenGL','renderer_acceptance':'not inferred from geometry; separate frame probe','pyvista':'0.48.4','features':'default standalone and rendering groups; Python; no Java/Qt/MPI/CUDA/OSPRay/OpenXR; upstream wheel packaging disables CTest'},indent=2))
run([sys.executable,'-m','pip','install','cmake==3.31.6','ninja','setuptools','wheel','delvewheel','pefile','numpy','pytest','pytest-timeout'])
# ARM64 import stubs target the Windows system DLL, not an alternate GL implementation.
u='https://raw.githubusercontent.com/mingw-w64/mingw-w64/3ad495b55f0524c61fa3d02dbd0cdeceabb0c038/mingw-w64-crt/lib-common/opengl32.def'
data=urllib.request.urlopen(u).read()
assert hashlib.sha256(data).hexdigest()=='d68950dfacc4ea3ce9c0e176084cf682e5be199b47c42bc4fdf6a1f8d4f93d66'
(work/'opengl32.def').write_bytes(data)
run(['lib','/nologo','/machine:arm64',f'/def:{work/"opengl32.def"}',f'/out:{work/"opengl32.lib"}'])
args=['cmake','-S',source,'-B',build,'-GNinja','-DCMAKE_BUILD_TYPE=Release','-DVTK_WHEEL_BUILD=ON','-DVTK_WRAP_PYTHON=ON','-DVTK_WRAP_JAVA=OFF','-DVTK_GROUP_ENABLE_Qt=NO','-DVTK_GROUP_ENABLE_MPI=NO','-DVTK_MODULE_ENABLE_VTK_RenderingOpenXR=NO','-DVTK_VERSION_SUFFIX=','-DVTK_BUILD_TESTING=OFF','-DVTK_BUILD_EXAMPLES=OFF','-DVTK_ENABLE_REMOTE_MODULES=OFF','-DVTK_USE_CUDA=OFF',f'-DPython3_EXECUTABLE={Path(sys.executable).as_posix()}',f'-DOPENGL_gl_LIBRARY={(work/"opengl32.lib").as_posix()}']
(out/'configure-command.json').write_text(json.dumps([str(a)for a in args],indent=2))
try:
    run(args)
    run(['cmake','--build',build,'--parallel','4'])
finally:
    if (build/'CMakeCache.txt').exists():shutil.copy(build/'CMakeCache.txt',out/'CMakeCache.txt')
    if (build/'CMakeFiles/CMakeConfigureLog.yaml').exists():shutil.copy(build/'CMakeFiles/CMakeConfigureLog.yaml',out/'CMakeConfigureLog.yaml')
run([sys.executable,'setup.py','bdist_wheel','--dist-dir',out/'raw'],build)
wheel=next((out/'raw').glob('*.whl'))
run([sys.executable,'-m','delvewheel','repair','--analyze-existing','-w',out/'wheels',wheel])
run([sys.executable,root/'ci/native/wheel_audit.py',out/'wheels',out/'wheel-audit.json'])
run([sys.executable,'-m','venv',work/'test-venv'])
py=work/'test-venv/Scripts/python.exe'
run([py,'-m','pip','install',next((out/'wheels').glob('*.whl')),'pyvista==0.48.4','pytest','pytest-timeout'])
run([py,'-m','pytest',root/'ci/native/test_vtk_oracles.py','-v','--timeout=180',f'--junitxml={out/"downstream.xml"}'])
for name in ['TestPointInPolygon.py','TestBoxPlaneIntersection.py','TestBoxSphereIntersection.py']:
    run([py,source/'Common/DataModel/Testing/Python'/name])
run([py,'-m','pip','freeze'])
(out/'CPU-PASS').write_text('Native wheel, PE/RECORD, PyVista geometry/volume/intersections and selected upstream VTK tests passed. No GPU/render claim.\n')
# Actual frame probe is separate, bounded and recorded even when unsupported.
try:
    subprocess.run([py,root/'ci/native/vtk_frame.py',out/'backend.json'],cwd=work,check=True,timeout=180)
except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as exc:
    (out/'backend-failure.txt').write_text(str(exc))
    raise
