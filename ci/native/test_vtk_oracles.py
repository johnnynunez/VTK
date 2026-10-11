"""Functional downstream VTK CPU geometry; no GPU claim."""
import numpy as np
import pytest
import pyvista as pv
import vtk


def test_clipping_volume_and_surface_intersections():
    volume = pv.ImageData(dimensions=(11, 11, 11), spacing=(0.1,0.1,0.1))
    assert volume.volume == pytest.approx(1)
    clipped = volume.clip(normal=(1,0,0), origin=(0.5,0,0), invert=False)
    assert clipped.volume == pytest.approx(0.5)
    box = pv.Box(bounds=(0,1,0,1,0,1)).triangulate()
    assert box.volume == pytest.approx(1)
    points, ids = box.ray_trace((-1,0.4,0.4),(2,0.4,0.4))
    assert len(points) == 2
    np.testing.assert_allclose(np.sort(points[:,0]), [0,1], atol=1e-6)
    assert len(ids) == 2
    with pytest.raises(AssertionError):
        assert clipped.volume == pytest.approx(1)


def test_tetrahedron_volume_and_wheel_version():
    assert vtk.vtkVersion.GetVTKVersion() == '9.6.2'
    cloud = pv.PolyData(np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]]))
    mesh = cloud.delaunay_3d()
    assert mesh.n_cells == 1
    assert mesh.volume == pytest.approx(1/6)
    assert mesh.celltypes.tolist() == [vtk.VTK_TETRA]


def test_opengl_backend_exists_without_claiming_render_support():
    from vtkmodules.vtkRenderingOpenGL2 import vtkWin32OpenGLRenderWindow
    window = vtkWin32OpenGLRenderWindow()
    assert window.IsA('vtkOpenGLRenderWindow')
    window.Finalize()
