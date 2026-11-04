import os
"""Style the system clock/calendar MAML layers while preserving their live updaters."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from PIL import Image
from io import BytesIO
import xml.etree.ElementTree as ET
import sys
source=Path(sys.argv[1]);target=Path(sys.argv[2]);target.parent.mkdir(parents=True,exist_ok=True)
changed=[]
with ZipFile(source)as src,ZipFile(target,'w',ZIP_DEFLATED)as dst:
 for info in src.infolist():
  name=info.filename;data=src.read(name)
  clock='/com.android.deskclock/'in name
  calendar=any('/'+p+'/'in name for p in ('com.android.calendar','com.xiaomi.calendar'))
  if calendar and '/2/fancy/manifest.xml'in name:
   root=ET.fromstring(data)
   for node in root.iter('Text'):node.set('color','#FFFFFF')
   data=ET.tostring(root,encoding='utf-8',xml_declaration=True);changed.append(name)
  if name.endswith('.png')and(calendar or clock)and'/0/'not in name:
   im=Image.open(BytesIO(data)).convert('RGBA');pixels=[]
   for r,g,b,a in im.getdata():
    if clock and (name.endswith('/bg.png')or'/quiet/'in name):a=a*(54*r+183*g+19*b)//(255*256)
    pixels.append((255,255,255,a*220//255))
   im.putdata(pixels);out=BytesIO();im.save(out,format='PNG');data=out.getvalue();changed.append(name)
  dst.writestr(info,data)
with ZipFile(source)as src,ZipFile(target)as dst:
 assert dst.testzip()is None and src.namelist()==dst.namelist()
 for name in src.namelist():
  if name.endswith('manifest.xml'):
   a=ET.fromstring(src.read(name));b=ET.fromstring(dst.read(name))
   assert a.attrib==b.attrib
   for tag in ('ExternalCommands','Function','FolmeState','FolmeConfig'):
    assert [ET.tostring(x)for x in a.findall(tag)]==[ET.tostring(x)for x in b.findall(tag)]
print(f'Styled {len(changed)} system MAML layers; date, hands and animation commands preserved')
