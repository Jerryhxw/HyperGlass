"""Build and sign the HyperGlass release APK with the configured release key."""
import argparse
import hashlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parent
MODULE=ROOT/'module'
B=MODULE/'.build'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--signing-dir',type=Path,required=True,help='Directory containing release.jks and keychain.properties')
parser.add_argument('--reference-dir',type=Path,default=ROOT/'fixtures/reference',help='Local launcher/runtime reference fixtures')
args=parser.parse_args()
signing=args.signing_dir.expanduser().resolve()
key=signing/'release.jks'
if not key.is_file():parser.error('release.jks is required; no signing-key fallback is available')
if os.environ.get('CI')=='true':
    required=['RELEASE_KEY_ALIAS','RELEASE_STORE_PASSWORD','RELEASE_KEY_PASSWORD']
    for name in required:
        if not os.environ.get(name):parser.error('Missing CI signing secret: '+name)
    alias=os.environ['RELEASE_KEY_ALIAS'];store_password=os.environ['RELEASE_STORE_PASSWORD'];key_password=os.environ['RELEASE_KEY_PASSWORD']
else:
    properties=signing/'keychain.properties'
    if not properties.is_file():parser.error('keychain.properties is required for local release signing')
    config={}
    for line in properties.read_text().splitlines():
        if '='in line and not line.lstrip().startswith('#'):
            name,value=line.split('=',1);config[name.strip()]=value.strip()
    for name in ['keyAlias','keychainService','keychainAccount']:
        if not config.get(name):parser.error('Missing signing property: '+name)
    result=subprocess.run(['/usr/bin/security','find-generic-password','-s',config['keychainService'],'-a',config['keychainAccount'],'-w'],capture_output=True,text=True)
    if result.returncode or not result.stdout.rstrip('\r\n'):parser.error('Release signing password is unavailable from macOS Keychain')
    alias=config['keyAlias'];store_password=key_password=result.stdout.rstrip('\r\n')
child_env=dict(os.environ,HYPERGLASS_RELEASE_PASSWORD=store_password,HYPERGLASS_RELEASE_KEY_PASSWORD=key_password,HYPERGLASS_REFERENCE_DIR=str(args.reference_dir.expanduser().resolve()))
from tools.build_env import SDK,BUILD_TOOLS as BT,ANDROID_JAR as JAR,TOOLCHAIN,CLANG as CC
CXX=TOOLCHAIN/'aarch64-linux-android35-clang++'
B.mkdir(exist_ok=True)
API=B/'api.jar'
if not API.exists():
    url='https://repo.maven.apache.org/maven2/io/github/libxposed/api/102.0.0/api-102.0.0.aar'
    with zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(url).read()))as archive:API.write_bytes(archive.read('classes.jar'))
def run(*arguments):subprocess.run(list(map(str,arguments)),check=True,env=child_env)
for script in ['icons/generate.py','icons/test_processor.py','transitions/generate.py','transitions/test_adapters.py','transitions/generate_engine.py','transitions/test_engine.py','widgets/generate.py','widgets/test_loader.py']:
    subprocess.run([sys.executable,str(ROOT/'adapters'/script)],check=True,env=dict(child_env,HG_ADAPTIVE='1'))
run(sys.executable,MODULE/'adaptive/catalog.py')
asset=B/'dynamicicons'
with zipfile.ZipFile(asset,'w',zipfile.ZIP_DEFLATED)as archive:
    for source in sorted((ROOT/'resources/dynamicicons').rglob('*')):
        name=source.relative_to(ROOT/'resources/dynamicicons').as_posix()+('/'if source.is_dir()else'')
        info=zipfile.ZipInfo(name,(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
        info.external_attr=((0o40755 if source.is_dir()else 0o100644)<<16)|(0x10 if source.is_dir()else 0)
        archive.writestr(info,b''if source.is_dir()else source.read_bytes())
(B/'assets.S').write_text('.section .rodata\n.global dynamic_start,dynamic_end\ndynamic_start:\n.incbin "'+str(asset)+'"\ndynamic_end:\n.section .note.GNU-stack,"",%progbits\n')
common=['-O2','-DNDEBUG','-Wall','-Wextra','-Werror','-fPIC','-fvisibility=hidden','-I'+str(B),'-I'+str(MODULE/'native')]
objects=[]
def compile_one(source,cpp=False,extra=()):
    output=B/(Path(source).stem+'.o');run(CXX if cpp else CC,'-std=c++17'if cpp else'-std=c11',*common,*extra,'-c',source,'-o',output);objects.append(output)
compile_one(MODULE/'native/module.c',extra=['-fno-builtin'])
compile_one(B/'assets.S',extra=['-Wno-unused-command-line-argument'])
for source in sorted((MODULE/'third_party/xz').glob('*.c')):
    compile_one(source,extra=['-DXZ_USE_CRC64','-DXZ_DEC_ARM64','-I'+str(MODULE/'third_party/xz')])
for name in ['elf_image','resolver','runtime','page_guard','material']:
    compile_one(MODULE/('native/'+name+'.cpp'),True,['-DXZ_USE_CRC64','-I'+str(MODULE/'third_party/xz')])
library=B/'libhyperglass.so'
run(CXX,'-shared','-static-libstdc++','-Wl,-z,max-page-size=16384','-Wl,-z,relro,-z,now','-Wl,--exclude-libs,ALL','-Wl,--version-script='+str(MODULE/'native/exports.map'),*objects,'-llog','-ldl','-landroid','-o',library)
release_library=B/'libhyperglass.release.so';shutil.copy2(library,release_library)
run(TOOLCHAIN/'llvm-strip','--strip-unneeded',release_library)
res=B/'res';shutil.rmtree(res,ignore_errors=True);res.mkdir()
run(BT/'aapt2','compile','--dir',MODULE/'res','-o',res)
run(BT/'aapt2','link','-I',JAR,'--manifest',MODULE/'AndroidManifest.xml','-o',B/'base.apk',*sorted(res.glob('*.flat')))
classes=B/'classes';shutil.rmtree(classes,ignore_errors=True);classes.mkdir()
run('javac','-g:none','--release','17','-classpath',str(JAR)+os.pathsep+str(API),'-d',classes,*sorted((MODULE/'src').rglob('*.java')))
dex=B/'dex';shutil.rmtree(dex,ignore_errors=True);dex.mkdir()
run(BT/'d8','--release','--min-api','35','--lib',JAR,'--classpath',API,'--output',dex,*sorted(classes.rglob('*.class')))
with zipfile.ZipFile(B/'base.apk')as source,zipfile.ZipFile(B/'unsigned.apk','w')as archive:
    for entry in source.infolist():archive.writestr(entry,source.read(entry.filename))
    archive.write(dex/'classes.dex','classes.dex',compress_type=zipfile.ZIP_DEFLATED)
    archive.write(release_library,'lib/arm64-v8a/libhyperglass.so',compress_type=zipfile.ZIP_STORED)
    for file in sorted((MODULE/'third_party').rglob('*')):
        if file.is_file()and file.name in ['COPYING','LICENSE','UPSTREAM','NOTICE']:archive.write(file,'assets/licenses/'+str(file.relative_to(MODULE/'third_party')),compress_type=zipfile.ZIP_DEFLATED)
    for file in sorted((MODULE/'META-INF').rglob('*')):
        if file.is_file():archive.write(file,str(file.relative_to(MODULE)),compress_type=zipfile.ZIP_DEFLATED)
run(BT/'zipalign','-P','16','-f','4',B/'unsigned.apk',B/'aligned.apk')
manifest=ET.parse(MODULE/'AndroidManifest.xml').getroot();android='{http://schemas.android.com/apk/res/android}'
version=manifest.attrib[android+'versionName'];output=ROOT/'dist'/('HyperGlass-LSPosed-'+version+'.apk');output.parent.mkdir(exist_ok=True)
run(BT/'apksigner','sign','--ks',key,'--ks-key-alias',alias,'--ks-pass','env:HYPERGLASS_RELEASE_PASSWORD','--key-pass','env:HYPERGLASS_RELEASE_KEY_PASSWORD','--lineage',ROOT/'config/signing-lineage.bin','--rotation-min-sdk-version','28','--v1-signing-enabled','false','--v2-signing-enabled','false','--v4-signing-enabled','false','--out',output,B/'aligned.apk')
verification=subprocess.run([str(BT/'apksigner'),'verify','--verbose','--print-certs',str(output)],check=True,capture_output=True,text=True,env=child_env)
print(verification.stdout,end='')
expected=(ROOT/'config/release-certificate.sha256').read_text().strip()
assert 'Signer #1 certificate SHA-256 digest: '+expected in verification.stdout,'Unexpected release certificate'

with zipfile.ZipFile(output)as archive:
    assert archive.testzip()is None
    assert archive.read('META-INF/xposed/scope.list')==b'com.miui.home\n'
    assert archive.read('META-INF/xposed/native_init.list')==b'libhyperglass.so\n'
    packed=archive.read('lib/arm64-v8a/libhyperglass.so')
    for marker in [b'PIXEL_PROBE',b'FORMAT_PROBE',b'DART_LAYOUT',b'hg-material-diag',b'hg-first.rgba',b'hg-last.rgba']:
        assert marker not in packed,marker
    from elftools.elf.elffile import ELFFile
    elf=ELFFile(io.BytesIO(packed));assert elf.get_section_by_name('.symtab')is None
    assert not any(section.name.startswith('.debug')for section in elf.iter_sections())
    exports=[s.name for s in elf.get_section_by_name('.dynsym').iter_symbols()if s['st_shndx']!='SHN_UNDEF'and s.name]
    assert exports==['native_init'],exports
output.with_suffix('.apk.sha256').write_text(hashlib.sha256(output.read_bytes()).hexdigest()+'  '+output.name+'\n')
print(output)
