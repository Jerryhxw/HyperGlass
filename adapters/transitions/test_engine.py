import os
"""Run the marked export scheduler and native backdrop continuations."""
from pathlib import Path
import struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
import unicorn.arm64_const as R
H=Path(__file__).resolve().parent
rows={int(r[0],16):bytes.fromhex(r[2]) for r in (l.split()for l in (H.parent/'engine-patches.txt').read_text().splitlines())}
assert [(a,len(c))for a,c in rows.items()]==[(0x6e81cc,4),(0xeaebbc,52)]
image=ELFFile(open(Path(os.environ.get('HYPERGLASS_REFERENCE_DIR',H.parents[1]/'fixtures/reference'))/'launcher-801027722/libhyper_os_flutter.so','rb'))
def original(va,n):
 s=next(s for s in image.iter_segments()if s['p_type']=='PT_LOAD'and s['p_vaddr']<=va<va+n<=s['p_vaddr']+s['p_filesz'])
 image.stream.seek(s['p_offset']+va-s['p_vaddr']);return image.stream.read(n)
for marked in [False,True]:
 for view in [0,7]:
  u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
  for a,n in [(0xeae000,8192),(0x734000,4096),(0x200000,8192),(0x300000,4096)]:u.mem_map(a,n)
  u.mem_write(0xeaebbc,rows[0xeaebbc]);u.mem_write(0x7348d8,bytes.fromhex('c0035fd6'))
  u.mem_write(0x200048,struct.pack('<Q',view|((1<<29)if marked else 0)))
  u.reg_write(R.UC_ARM64_REG_X19,0x200000);u.reg_write(R.UC_ARM64_REG_X25,0x201000);u.reg_write(R.UC_ARM64_REG_SP,0x300000)
  calls=[]
  def queue(u,pc,size,data):
   if pc==0x7348d8:calls.append(tuple(u.reg_read(r)for r in [R.UC_ARM64_REG_X0,R.UC_ARM64_REG_X1,R.UC_ARM64_REG_X2]))
  u.hook_add(UC_HOOK_CODE,queue);u.emu_start(0xeaebbc,0xeaebf0,count=20)
  assert calls==[(0x201000,0x300100,0)]
  assert struct.unpack('<Q',u.mem_read(0x200048,8))[0]==view|((1<<29)if marked else 0)
  assert u.reg_read(R.UC_ARM64_REG_SP)==0x300000 and u.reg_read(R.UC_ARM64_REG_X19)==0x200000
print('PASS: exports queue without an artificial delay; the original owned callback, view id, stack and queue survive')
# Every window policy retains the owned raster backdrop across surface loss;
# the original entry-policy transitions and texture ownership still execute.
for policy in range(4):
 u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.mem_map(0x6e8000,4096);u.mem_map(0x200000,4096)
 u.mem_write(0x6e81a8,original(0x6e81a8,0x34));u.mem_write(0x6e81cc,rows[0x6e81cc]);u.mem_write(0x6e8100,original(0x6e8100,8))
 u.mem_write(0x200038,struct.pack('<I',policy));u.reg_write(R.UC_ARM64_REG_X23,0x200000);u.reg_write(R.UC_ARM64_REG_X20,1)
 u.emu_start(0x6e81a8,0x6e81dc,count=30)
 assert u.reg_read(R.UC_ARM64_REG_X20)==0
 assert struct.unpack('<I',u.mem_read(0x200038,4))[0]==({1:3,2:0}.get(policy,policy))
print('PASS: retained window backdrop preserves native ownership and entry policy')
# Reject outside branches into the middle of the replacement scheduling block.
import capstone
md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM);md.detail=True
for segment in image.iter_segments():
 if segment['p_type']=='PT_LOAD'and segment['p_flags']&1:
  for ins in md.disasm(segment.data(),segment['p_vaddr']):
   if not 0xeaebbc<=ins.address<0xeaebf0 and ins.mnemonic.startswith(('b','cb','tb')) and ins.operands and ins.operands[-1].type==capstone.CS_OP_IMM:
    assert not 0xeaebbc<ins.operands[-1].imm<0xeaebf0,(hex(ins.address),ins.op_str)
print('PASS: the scheduler replacement has no external interior branch targets')
