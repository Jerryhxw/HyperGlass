import os
"""Build semantic address recipes from an unmodified reference image.

Source RVAs identify training instructions only. Consumers resolve code in the
loaded image by symbols, instruction neighborhoods and corroborated call edges.
"""
from dataclasses import dataclass
from pathlib import Path
import struct,collections,bisect
from inspect_pair import Image,words

def arm_mask(w,frames=True):
 if w&0x7c000000==0x14000000:return 0xfc000000
 if w&0xff000010==0x54000000:return 0xff00001f
 if w&0x7e000000==0x34000000:return 0xff00001f
 if w&0x7e000000==0x36000000:return 0xfff8001f
 if w&0x1f000000==0x10000000:return 0x9f00001f
 if w&0x3b000000==0x18000000:return 0xff00001f
 rn=(w>>5)&31;rd=w&31
 if w&0x3b000000==0x39000000:return 0xffffffff if frames and rn in (15,29,31) else 0xffc003ff
 if w&0x3b200000==0x38000000:return 0xffffffff if frames and rn in (15,29,31) else 0xffe00fff
 if w&0x1f800000==0x12800000:return 0xffe0001f
 if w&0x1f000000==0x11000000:return 0xffffffff if frames and rn==rd and rn in (15,29,31) else 0xff8003ff
 return 0xffffffff

def control_mask(w,mask):
 # Only branch promotion/suppression uses operand-role matching. Injected
 # adapters always retain the exact register ABI in their address recipes.
 if w&0x7c000000==0x14000000 or w&0xff000010==0x54000000:return mask
 positions=[0,5]
 if w&0x1f000000 not in [0x11000000,0x10000000]and w&0x3b000000!=0x39000000 and w&0x3b200000!=0x38000000:positions.append(16)
 for shift in positions:
  reg=(w>>shift)&31
  if reg<=7:mask&=~(31<<shift)
 return mask

def branch_target(w,pc):
 if w&0x7c000000==0x14000000:bits,scale=26,0
 elif w&0xff000010==0x54000000 or w&0x7e000000==0x34000000:bits,scale=19,5
 elif w&0x7e000000==0x36000000:bits,scale=14,5
 else:return None
 v=(w>>scale)&((1<<bits)-1);v=v-(1<<bits)if v&(1<<(bits-1))else v
 return pc+v*4

def immediate(w):
 if w&0x1f800000==0x12800000:
  n=((w>>5)&65535)<<(((w>>21)&3)*16)
  if w&0x60000000==0:n=~n
  if not w>>31:n&=0xffffffff
  return n
 if w&0x1f000000==0x11000000:return ((w>>10)&4095)<<(12 if w&(1<<22)else 0)
 if w&0x3b000000==0x39000000:return ((w>>10)&4095)<<(w>>30)
 if w&0x3b200000==0x38000000:
  n=(w>>12)&511;return n-512 if n&256 else n
 raise ValueError(hex(w))

def edit_suffix(pattern,masks,target):
 # Target-prefix omission is free; both sequences must end at the core.
 prev=[0]*(len(target)+1)
 for i,(value,mask)in enumerate(zip(pattern,masks),1):
  cur=[i]
  for j,w in enumerate(target,1):cur.append(min(prev[j]+1,cur[-1]+1,prev[j-1]+(0 if value&mask==w&mask else 3)))
  prev=cur
 return prev[-1]

@dataclass
class Anchor:
 va:int
 owner:str
 offset:int
 before:int
 values:tuple
 masks:tuple
 mode:int=0
 dependency:int=-1
 qualifier:int=-1
 callee:str=""
 delta:int=0

class Model:
 def __init__(self,path):
  self.image=Image(path);self.anchors=[];self.by_va={};self.callers=collections.defaultdict(list)
  for base,data in self.image.loads:
   for i,w in enumerate(words(data[:len(data)//4*4])):
    if w&0xfc000000==0x94000000:self.callers[branch_target(w,base+i*4)].append(base+i*4)
 def add(self,va,frames=None,control=False):
  if va in self.by_va:return self.by_va[va]
  s=self.image.owner(va);lo,hi=self.image.extent(s)
  if va in self.image.imports:s=(va,16,'@plt:'+self.image.imports[va]);lo,hi=va,va+16
  elif hi<=va:hi=va+44
  if frames is None:frames=not ('prepareIconLayers'in s[2]or'_textStyleWithFontSize'in s[2])
  before,after=(8,9)if control else(10,11)
  if control and s[2]=='IconComposer.applyStyle':before,after=2,1
  start=max(lo,va-before*4);end=min(hi,va+after*4)
  values=words(self.image.read(start,end-start));masks=tuple(control_mask(w,arm_mask(w,frames))if control else arm_mask(w,frames)for w in values)
  a=Anchor(va,s[2],va-s[0],(va-start)//4,values,masks)
  index=len(self.anchors);self.by_va[va]=index;self.anchors.append(a)
  if control and s[2]=='MiuiWidgetGetxController.handleClick'and va in [0x148083c,0x1480844]:
   a.mode=2;a.callee='BlurUtilities.isGlassMaterialSupported';a.delta=-4 if va==0x148083c else 4
  if control and s[2]=='TextureBox.paint':a.mode=3;a.delta=112
  if va in self.image.imports:a.mode=4;a.callee=self.image.imports[va]
  # Allocator/outlined stubs have no own Dart debug symbol. A named caller's
  # validated BL gives their entry without relying on a neighboring label.
  if a.mode==0 and va>=s[0]+s[1] and va in self.callers:
   choices=[]
   for pc in self.callers[va]:
    c=self.image.owner(pc)
    if pc<c[0]+c[1] and len(self.image.names[c[2]])==1:choices.append(pc)
   if choices:
    pc=min(choices,key=lambda p:abs(p-self.image.owner(p)[0]))
    a.dependency=self.add(pc);a.mode=1
  if len(self.image.names[s[2]])>1:
   for pc in self.callers[s[0]]:
    c=self.image.owner(pc)
    if c[2]!=s[2]and pc<c[0]+c[1]and len(self.image.names[c[2]])==1:
     a.qualifier=self.add(pc);break
  return index
 def resolve(self,target,index,cache=None):
  if cache is None:cache={}
  if index in cache:return cache[index]
  a=self.anchors[index];cache[index]=None
  if a.mode==5:
   marker=self.resolve(target,a.dependency,cache)
   if marker is None:return None
   destinations={s[0]for s in target.names[a.callee]};matches=[]
   for symbol in target.names[a.owner]:
    lo,hi=target.extent(symbol)
    if not lo<=marker<hi:continue
    for pc in range(marker,hi,4):
     word=struct.unpack('<I',target.read(pc,4))[0]
     if word&0xfc000000==0x94000000 and branch_target(word,pc)in destinations:
      result=pc+a.delta;core=struct.unpack('<I',target.read(result,4))[0]
      if core&a.masks[a.before]==a.values[a.before]&a.masks[a.before]:matches.append(result)
      break
   if len(set(matches))==1:cache[index]=matches[0]
   return cache[index]
  if a.mode==4:
   matches=[va for va,name in target.imports.items()if name==a.callee]
   if len(matches)==1:cache[index]=matches[0]
   return cache[index]
  if a.mode==3:
   matches=[]
   for symbol in target.names[a.owner]:
    lo,hi=target.extent(symbol)
    for i,w in enumerate(words(target.read(lo,hi-lo))):
     if w&0xfc000000!=0x94000000:continue
     pc=lo+i*4;callee=branch_target(w,pc)
     try:first,second,third=struct.unpack('<3I',target.read(callee,12))
     except ValueError:continue
     if first&0xff80001f!=0xd2800002 or second&0xff80001f!=0xf2800002 or third&0xfc000000!=0x14000000:continue
     tag=immediate(first)|(((second>>5)&65535)<<(((second>>21)&3)*16))
     if (tag&255)==0x1c and ((tag>>8)&15)*16>=a.delta:matches.append(pc)
   if len(set(matches))==1:cache[index]=matches[0]
   return cache[index]
  if a.mode==2:
   destinations={s[0]for s in target.names[a.callee]};matches=[]
   for symbol in target.names[a.owner]:
    lo,hi=target.extent(symbol)
    for i,w in enumerate(words(target.read(lo,hi-lo))):
     pc=lo+i*4
     if w&0xfc000000==0x94000000 and branch_target(w,pc)in destinations:
      if any(struct.unpack('<I',target.read(pc+off,4))[0]&0xfff8001f!=0x37200000 for off in [-4,4]):continue
      result=pc+a.delta;instruction=struct.unpack('<I',target.read(result,4))[0]
      if instruction&a.masks[a.before]==a.values[a.before]&a.masks[a.before]:matches.append(result)
   if len(set(matches))==1:cache[index]=matches[0]
   return cache[index]
  if a.mode==1:
   pc=self.resolve(target,a.dependency,cache)
   if pc is None:return None
   out=branch_target(struct.unpack('<I',target.read(pc,4))[0],pc)
   # Require the allocator/outlined stub's first semantic words as well.
   if out is None:return None
   old=self.image.read(a.va,min(12,len(a.values)*4));new=target.read(out,len(old))
   if not all((x&arm_mask(x,False))==(y&arm_mask(x,False))for x,y in zip(words(old),words(new))):return None
   cache[index]=out;return out
  qualifier=None
  if a.qualifier>=0:
   pc=self.resolve(target,a.qualifier,cache)
   if pc is None:return None
   qualifier=branch_target(struct.unpack('<I',target.read(pc,4))[0],pc)
  candidates=[]
  symbols=list(target.names[a.owner]);seen={s[0]for s in symbols};prefix=a.owner.rsplit('.',1)[0]+'.'
  # Small methods can delegate a color/style operation to a new private helper.
  for _ in range(2):
   added=[]
   for entry in symbols:
    lo,hi=target.extent(entry)
    for off,w in enumerate(words(target.read(lo,hi-lo))):
     if w&0xfc000000!=0x94000000:continue
     pc=branch_target(w,lo+off*4)
     child=target.owner(pc)
     if child[0]==pc and child[2].startswith(prefix)and pc not in seen:added.append(child);seen.add(pc)
   symbols+=added
   if not added:break
  for symbol in symbols:
   if qualifier is not None and symbol[0]!=qualifier:continue
   base,end=target.extent(symbol);data=words(target.read(base,end-base))
   core=a.values[a.before];mask=a.masks[a.before]
   for i,w in enumerate(data):
    if w&mask!=core&mask:continue
    before=min(i,a.before+2);after=min(len(data)-i-1,len(a.values)-a.before-1+2)
    left=edit_suffix(a.values[:a.before],a.masks[:a.before],data[i-before:i])
    right=edit_suffix(tuple(reversed(a.values[a.before+1:])),tuple(reversed(a.masks[a.before+1:])),tuple(reversed(data[i+1:i+1+after])))
    if left+right<=2:candidates.append((left+right,base+i*4))
  exact={v for score,v in candidates if score==0};possible=exact or{v for score,v in candidates}
  if len(possible)==1:cache[index]=next(iter(possible))
  return cache[index]
