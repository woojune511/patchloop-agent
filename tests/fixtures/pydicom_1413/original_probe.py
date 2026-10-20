import io
import sys
print({'stage': 'imports', 'sys_path0': sys.path[0]}, flush=True)
from pydicom.tag import Tag
from pydicom.dataelem import DataElement
from pydicom.filewriter import write_data_element
from pydicom.filebase import DicomBytesIO

# Construct two OL elements with different input shapes.
elem_list = DataElement(Tag(0x00660041), 'OL', [1, 2, 3])
elem_bytes = DataElement(Tag(0x00660041), 'OL', b'\x01\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00')

check_setup('list_vr', elem_list.VR, 'OL')
check_setup('bytes_vr', elem_bytes.VR, 'OL')
check_setup('list_value_type', type(elem_list.value).__name__, 'MultiValue')
check_setup('bytes_value_type', type(elem_bytes.value).__name__, 'bytes')

results = {}
for name, elem in [('list', elem_list), ('bytes', elem_bytes)]:
    fp = DicomBytesIO()
    fp.is_little_endian = True
    fp.is_implicit_VR = False
    print({'stage': 'before_write', 'name': name, 'value_type': type(elem.value).__name__, 'vm': elem.VM}, flush=True)
    try:
        write_data_element(fp, elem)
        results[name] = {'ok': True, 'len': len(fp.getvalue()), 'prefix': fp.getvalue()[:16].hex()}
    except Exception as exc:
        results[name] = {'ok': False, 'exc_type': type(exc).__name__, 'exc': str(exc)}
        print({'stage': 'write_error', 'name': name, 'exc_type': type(exc).__name__, 'exc': str(exc)}, flush=True)

print({'stage': 'final', 'results': results}, flush=True)
