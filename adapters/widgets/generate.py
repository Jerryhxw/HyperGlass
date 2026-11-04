import os
from pathlib import Path
import subprocess,struct,json
from elftools.elf.elffile import ELFFile
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.build_env import CLANG
cc=CLANG
subprocess.run([str(cc),'-Oz','-fno-builtin','-fno-stack-protector','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-ffreestanding','-ffunction-sections','-fno-pic','-fno-pie','-nostdlib','-static',f'-Wl,-T,{H/"layout.ld"},-e,parse_hook,--build-id=none',str(H/'loader.c'),str(H/'entry.S'),'-o',str(H/'loader.elf')],check=True)
source=ELFFile(open(Path(os.environ.get('HYPERGLASS_REFERENCE_DIR',ROOT/'fixtures/reference'))/'launcher-801027722/librust_maml_sdk.so','rb'));linked=ELFFile(open(H/'loader.elf','rb'));patches=[]
def raw(va,n):
 for s in source.iter_segments():
  if s['p_type']=='PT_LOAD'and s['p_vaddr']<=va and va+n<=s['p_vaddr']+s['p_filesz']:
   source.stream.seek(s['p_offset']+va-s['p_vaddr']);return source.stream.read(n)
 raise ValueError(hex(va))
def patch(va,data,reason):patches.append(dict(vaddr=f'{va:x}',expected=raw(va,len(data)).hex(),replacement=data.hex(),reason=reason))
limits={'.xml_helpers':(0x33affc,2676),'.xml_attrs':(0x4156e8,2160),'.xml_transform':(0x33bd60,1720),'.xml_data':(0x416a60,1508)}
for name,(base,n)in limits.items():
 sec=linked.get_section_by_name(name);assert sec['sh_addr']+sec['sh_size']<=base+n,(name,sec['sh_size'],n)
 patch(base,bytes.fromhex('00008052c0035fd6'),'Omit regex diagnostic formatting to reserve the native widget adapter')
 code=sec.data();code+=b'\0'*(-len(code)%4)
 for off in range(0,len(code),256):patch(sec['sh_addr']+off,code[off:off+256],'Common MAML DOM loader: native material and foreground; no resource identifiers')
 print(name,len(code),'bytes')
for s in linked.iter_sections():
 if s['sh_type']in ['SHT_REL','SHT_RELA']:assert s['sh_size']==0
symbols={s.name:s['st_value']for s in linked.get_section_by_name('.symtab').iter_symbols()}
delta=symbols['parse_hook']-0x5182e4;assert delta%4==0 and abs(delta)<1<<27
patch(0x5182e4,struct.pack('<I',0x14000000|((delta//4)&0x3ffffff)),'Transform Widget manifests at the common native parser; original files stay intact')
end=0
for p in sorted(patches,key=lambda p:int(p['vaddr'],16)):
 va=int(p['vaddr'],16);assert va>=end;end=va+len(bytes.fromhex(p['replacement']))
assert len(patches)<=64
(H/'profile.json').write_text(json.dumps(dict(image='librust_maml_sdk.so',patches=patches),indent=2)+'\n')
(H.parent/'widget-patches.txt').write_text(''.join(f"{p['vaddr']} {p['expected']} {p['replacement']}\n"for p in patches))
print('PASS:',len(patches),'bounded native widget sites')
