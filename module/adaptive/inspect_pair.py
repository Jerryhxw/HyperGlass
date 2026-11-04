import os
"""Compare semantic instruction neighborhoods across two unmodified ELF images."""
import sys,struct,bisect,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from sym_lookup import get_syms
from elftools.elf.elffile import ELFFile
class Image:
 def __init__(self,path):
  self.path=Path(path);self.elf=ELFFile(self.path.open('rb'));self.symbols=get_syms(path);self.starts=[s[0]for s in self.symbols];self.names=collections.defaultdict(list)
  for s in self.symbols:self.names[s[2]].append(s)
  self.imports={}
  rel=self.elf.get_section_by_name('.rela.plt');plt=self.elf.get_section_by_name('.plt')
  if rel is not None and plt is not None:
   dyn=self.elf.get_section(rel['sh_link'])
   for i,record in enumerate(rel.iter_relocations()):self.imports[plt['sh_addr']+32+i*16]=dyn.get_symbol(record['r_info_sym']).name
  self.loads=[(s['p_vaddr'],s.data())for s in self.elf.iter_segments()if s['p_type']=='PT_LOAD']
 def read(self,va,size):
  for base,data in self.loads:
   if base<=va and va+size<=base+len(data):return data[va-base:va-base+size]
  raise ValueError(hex(va))
 def owner(self,va):
  i=bisect.bisect_right(self.starts,va)-1
  if i<0:raise ValueError(hex(va))
  return self.symbols[i]
 def extent(self,s):
  i=bisect.bisect_right(self.starts,s[0]);end=self.starts[i]if i<len(self.starts)else s[0]+s[1]
  return s[0],max(end,s[0]+s[1])
def mask(w):
 if w&0x7c000000==0x14000000:return 0xfc000000
 if w&0xff000010==0x54000000:return 0xff00001f
 if w&0x7e000000==0x34000000:return 0xff00001f
 if w&0x7e000000==0x36000000:return 0xfff8001f
 if w&0x1f000000==0x10000000:return 0x9f00001f
 if w&0x3b000000==0x18000000:return 0xff00001f
 # Object-pool slot addresses can move independently of the target function.
 if w&0x3b000000==0x39000000:return 0xffc003ff
 if w&0x3b200000==0x38000000:return 0xffe00fff
 if w&0x1f800000==0x12800000:return 0xffe0001f
 if w&0x1f000000==0x11000000:return 0xff8003ff
 return 0xffffffff
def words(data):return struct.unpack('<'+'I'*(len(data)//4),data)
def locate(old,new,va,before=6,after=8):
 s=old.owner(va);lo,hi=old.extent(s);start=max(lo,va-before*4);end=min(hi,va+after*4);source=words(old.read(start,end-start));m=[mask(w)for w in source];result=[]
 for t in new.names[s[2]]:
  a,b=new.extent(t);data=words(new.read(a,b-a))
  for off in range(len(data)-len(source)+1):
   if all((x&z)==(y&z)for x,y,z in zip(source,data[off:],m)):result.append(a+off*4+va-start)
 return s,result
if __name__=='__main__':
 import json
 old,new=Image(sys.argv[1]),Image(sys.argv[2]);print('symbols',len(old.symbols),len(new.symbols))
 profile=json.loads(Path(sys.argv[3]).read_text());counts=collections.Counter()
 for p in profile['patches']:
  va=int(p['vaddr'],16);s,result=locate(old,new,va);counts[len(result)]+=1
  print(hex(va),len(result),[hex(v)for v in result],s[2],hex(va-s[0]))
 print('candidate counts',dict(counts))
