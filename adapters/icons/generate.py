import os
import json,subprocess,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.build_env import CLANG
TOOL=CLANG
elf=HERE/'processor.elf'
subprocess.run([str(TOOL),'-Oz','-ffreestanding','-fno-builtin','-fno-stack-protector','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-mgeneral-regs-only','-ffunction-sections','-nostdlib','-static',f'-Wl,-T,{HERE / "layout.ld"},-e,entry,--build-id=none',str(HERE/'entry.S'),str(HERE/'mask.c'),'-o',str(elf)],check=True)
e=ELFFile(elf.open('rb'));code=e.get_section_by_name('.text').data()
assert len(code)+16<=0x18c7d48-0x18c78c4
helper=e.get_section_by_name('.text.helper').data()
assert len(helper)<=812
assert all(s.num_relocations()==0 for s in e.iter_sections() if s['sh_type'] in ('SHT_REL','SHT_RELA'))
profile=json.loads((ROOT/'baseline-profile.json').read_text())
# Foregrounds are normalized once during image creation; MAML has its own
# content transform. Keep the original disabled-app filter policy so every
# visible icon does not introduce a redundant offscreen ColorFilter layer.
profile['patches']=[p for p in profile['patches'] if p['vaddr'] in ['1721c84','1721d50','1488f18','19bfc68']]
source=Path(os.environ.get('HYPERGLASS_REFERENCE_DIR',ROOT.parent/'fixtures/reference'))/'launcher-801027722/libapp.so'
image=ELFFile(source.open('rb'))
def read(va,n):
 for s in image.iter_segments():
  if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va and va+n<=s['p_vaddr']+s['p_filesz']:
   image.stream.seek(s['p_offset']+va-s['p_vaddr']);return image.stream.read(n)
 raise ValueError(hex(va))
def patch(va,code,reason):
 profile['patches'].append(dict(vaddr=f'{va:x}',expected=read(va,len(code)).hex(),replacement=code.hex(),reason=reason))
def branch(at,to,link=False):return struct.pack('<I',(0x94000000 if link else 0x14000000)|(((to-at)//4)&0x3ffffff))
patch(0x18c3fa0,branch(0x18c3fa0,0x18c3fb4),'Normalize themed icon output with or without theme filters')
patch(0x18c7598,branch(0x18c7598,0x18c7604),'Skip optional receiver metadata for normalized processing')
patch(0x18c7604,struct.pack('<III',0xaa1603e2,0x928025f1,0xf8316ba2)+branch(0x18c7610,0x18c765c),'Initialize the saved filter-list slot to Dart null before async pixel extraction')
patch(0x18c7784,branch(0x18c7784,0x18c78c4,True),'Produce a normalized white foreground mask from premultiplied RGBA')
patch(0x18c7788,branch(0x18c7788,0x18c7d50),'Proceed directly to original premultiplication and image upload')
for off in range(0,len(helper),256):patch(0x8f9120+off,helper[off:off+256],'Relocation-free straight-alpha color helper in replaced unpremultiply body')
for off in range(0,len(code),256):patch(0x18c78c4+off,code[off:off+256],'Relocation-free Dart/native bridge and foreground normalization processor')
patch(0x18c3a6c,branch(0x18c3a6c,0x18c3abc),'Use the existing themed renderer and async safepoints for default icons as well')
patch(0x18c4024,struct.pack('<IIII',0x928029f1,0xf8316ba2,0x928028f1,0xf8316bb6)+branch(0x18c4034,0x18c4294),'Return the normalized image through original cleanup; omit theme background recomposition')
profile['scope']='Runtime color-distance foreground normalization over native glass; Launcher 7722'
(HERE/'profile.json').write_text(json.dumps(profile,indent=2)+'\n')
(HERE/'patches.txt').write_text(''.join(f"{p['vaddr']} {p['expected']} {p['replacement']}\n" for p in profile['patches']))
print('processor',len(code),'bytes; profile',len(profile['patches']),'sites')
