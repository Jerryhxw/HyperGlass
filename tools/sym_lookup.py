import sys, lzma, io, re
from elftools.elf.elffile import ELFFile

def get_syms(path):
    elf = ELFFile(open(path,'rb'))
    for sec in elf.iter_sections():
        if sec.name == '.gnu_debugdata':
            dec = lzma.decompress(sec.data())
            inner = ELFFile(io.BytesIO(dec))
            for s in inner.iter_sections():
                if s.name == '.symtab':
                    out=[]
                    for x in s.iter_symbols():
                        if x.name and x['st_value']:
                            out.append((x['st_value'], x['st_size'], x.name))
                    return sorted(out)
    return []

if __name__=='__main__':
    path = sys.argv[1]
    pat = re.compile(sys.argv[2], re.I)
    syms = get_syms(path)
    print(f'{len(syms)} symbols')
    n=0
    for va,sz,name in syms:
        if pat.search(name):
            print(f'{va:#x} {sz:6d} {name}')
            n+=1
            if n>200: break
