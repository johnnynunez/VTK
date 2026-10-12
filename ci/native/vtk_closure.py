"""Strict all-MZ/RECORD/ABI and bundled import-symbol closure audit."""
import email
import json
from pathlib import Path
import sys
import zipfile
import pefile
from delvewheel import _dll_list
from wheel_audit import audit


def inspect(wheel):
    result = audit(wheel)
    assert result['all_native_arm64']
    assert wheel.name == 'vtk-9.6.2-cp312-cp312-win_arm64.whl'
    assert 'Tag: cp312-cp312-win_arm64' in result['wheel_metadata']
    pefile.MAX_IMPORT_SYMBOLS = 1000000
    pefile.MAX_IMPORT_NAME_LENGTH = 65536
    objects = {}
    missing = []
    symbol_errors = []
    external = set()
    with zipfile.ZipFile(wheel) as z:
        meta = email.message_from_bytes(z.read('vtk-9.6.2.dist-info/METADATA'))
        assert (meta['Name'], meta['Version']) == ('vtk', '9.6.2')
        for entry in result['native']:
            name = Path(entry['path']).name.lower()
            assert name not in objects, ('Duplicate native basename', name)
            pe = pefile.PE(data=z.read(entry['path']), fast_load=True)
            pe.parse_data_directories(directories=[0, 1, 13])
            assert not any('too many' in w.lower() for w in pe.get_warnings()), pe.get_warnings()
            objects[name] = pe
        for name, pe in objects.items():
            for table in ('DIRECTORY_ENTRY_IMPORT', 'DIRECTORY_ENTRY_DELAY_IMPORT'):
                for entry in getattr(pe, table, []):
                    dll = entry.dll.decode().lower()
                    if dll in objects:
                        provider = objects[dll]
                        exports = getattr(getattr(provider, 'DIRECTORY_ENTRY_EXPORT', None), 'symbols', [])
                        names = {s.name for s in exports if s.name}
                        ordinals = {s.ordinal for s in exports}
                        for symbol in entry.imports:
                            if (symbol.name is not None and symbol.name not in names) or (symbol.name is None and symbol.ordinal not in ordinals):
                                symbol_errors.append([name, dll, symbol.name.decode() if symbol.name else symbol.ordinal])
                    elif dll in _dll_list.ignore_names_arm64 or dll.startswith(('api-ms-', 'ext-ms-')) or dll in {'python312.dll', 'vcruntime140.dll', 'vcruntime140_1.dll'}:
                        external.add(dll)
                    else:
                        missing.append([name, dll, table])
        # Never infer ABI solely from a filename/tag.
        python_imports = {e.dll.decode().lower() for pe in objects.values() for table in ('DIRECTORY_ENTRY_IMPORT', 'DIRECTORY_ENTRY_DELAY_IMPORT') for e in getattr(pe, table, []) if e.dll.decode().lower().startswith('python')}
        assert python_imports == {'python312.dll'}, python_imports
    for pe in objects.values(): pe.close()
    result.update(missing_imports=missing, missing_symbols=symbol_errors, external_system_or_cpython=sorted(external), import_closure=not missing and not symbol_errors)
    return result


if __name__ == '__main__':
    result = inspect(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2))
    print('Native payloads:', len(result['native']), 'missing imports:', len(result['missing_imports']), 'missing symbols:', len(result['missing_symbols']))
    assert result['import_closure'], 'Incomplete DLL/import-symbol closure; inspect report'
