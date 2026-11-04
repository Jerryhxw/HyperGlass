import os
"""Use the current window's glass backdrop for offscreen exports."""
import struct
from pathlib import Path
from elftools.elf.elffile import ELFFile

HERE = Path(__file__).resolve().parent
image = ELFFile(open(Path(os.environ.get('HYPERGLASS_REFERENCE_DIR',HERE.parents[1]/'fixtures/reference')) / 'launcher-801027722/libhyper_os_flutter.so', 'rb'))

def original(address, size):
    for segment in image.iter_segments():
        if (segment['p_type'] == 'PT_LOAD' and segment['p_vaddr'] <= address
                and address + size <= segment['p_vaddr'] + segment['p_filesz']):
            image.stream.seek(segment['p_offset'] + address - segment['p_vaddr'])
            return image.stream.read(size)
    raise ValueError(hex(address))

def branch(address, target, link=False):
    delta = target - address
    assert delta % 4 == 0 and -(1 << 27) <= delta < (1 << 27)
    return struct.pack('<I', (0x94000000 if link else 0x14000000) | ((delta // 4) & 0x3ffffff))

# Preserve the previous backdrop while a window surface is replaced.
# Marked exports carry their stage into the native raster callback.
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.build_env import CLANG
cc=CLANG
subprocess.run([str(cc),'-nostdlib','-static','-Wl,-Ttext=0xeaebbc,-e,settle_schedule,--build-id=none,--defsym,post_delayed_task=0x7348d8',str(HERE/'settle.S'),'-o',str(HERE/'settle.elf')],check=True)
linked=ELFFile(open(HERE/'settle.elf','rb'))
code=linked.get_section_by_name('.text').data();assert len(code)==52
patches=[(0x6e81cc,bytes.fromhex('f4031f2a')),
         (0xeaebbc,code)]
(HERE.parent/'engine-patches.txt').write_text(''.join(
 f'{at:x} {original(at,len(data)).hex()} {data.hex()}\n'for at,data in patches))
print('PASS: two bounded native backdrop and marked-export scheduling sites')
