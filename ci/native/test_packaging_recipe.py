"""Regression for the real missing vtkChartsCore DLL packaging failure."""
import ast
from pathlib import Path

def test_repair_supplies_runtime_search_path():
    tree = ast.parse(Path(__file__).with_name('build_vtk.py').read_text())
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'run']
    repairs = [c for c in calls if c.args and isinstance(c.args[0], ast.List) and any(isinstance(x, ast.Constant) and x.value == 'repair' for x in c.args[0].elts)]
    assert len(repairs) == 1
    literals = [x.value for x in repairs[0].args[0].elts if isinstance(x, ast.Constant)]
    assert '--add-path' in literals, 'Missing build/bin search path: vtkChartsCore-9.6.2.dll cannot be found'
    assert '--no-mangle' in literals
    assert '--ignore-missing' not in literals
