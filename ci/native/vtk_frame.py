"""Bound externally: actual two-frame readback, software/GPU unspecified."""
import json
from pathlib import Path
import sys
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
out=Path(sys.argv[1])
window=vtk.vtkRenderWindow()
window.SetOffScreenRendering(1)
window.SetSize(64,64)
renderer=vtk.vtkRenderer();window.AddRenderer(renderer)
report={'backend':window.GetClassName(),'gpu_claim':False,'frame_verified':False}
out.write_text(json.dumps(report,indent=2))
frames=[]
for color in [(1,0,0),(0,0,1)]:
    renderer.SetBackground(*color)
    window.Render()
    capture=vtk.vtkWindowToImageFilter();capture.SetInput(window);capture.ReadFrontBufferOff();capture.Update()
    frames.append(vtk_to_numpy(capture.GetOutput().GetPointData().GetScalars()).copy())
report['capabilities']=window.ReportCapabilities()
report['center_pixels']=[a[len(a)//2].tolist() for a in frames]
assert frames[0].shape==frames[1].shape and frames[0].size > 0
assert frames[0][:,0].mean() > 200 and frames[0][:,2].mean() < 10
assert frames[1][:,2].mean() > 200 and frames[1][:,0].mean() < 10
assert not np.array_equal(frames[0],frames[1]), 'unchanged readback negative control'
report['frame_verified']=True
out.write_text(json.dumps(report,indent=2))
window.Finalize()
