from dexvideo.paths import stage
from pathlib import Path
from PIL import Image
import numpy as np,json,hashlib,shutil,argparse
p=argparse.ArgumentParser();p.add_argument('--preview',action='store_true');a=p.parse_args()
R=(stage('parade') / '');V=R/'v3';out=V/('preview_composite' if a.preview else 'frames');out.mkdir(exist_ok=True)
frames=[90,220] if a.preview else range(1,361)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def path(stage,f):
 if stage=='all':return (V/'preview/all' if a.preview else R/'v2/frames')/f'frame_{f:04d}.png'
 return V/('preview' if a.preview else 'layers')/stage/f'frame_{f:04d}.png'
def mix(p0,p1,alpha):
 im0=Image.open(p0).convert('RGB');im1=Image.open(p1).convert('RGB');assert im0.size==im1.size
 # An editorial dissolve in display space, confined to camera movement.
 arr=np.array(im0,dtype=np.float32)*(1-alpha)+np.array(im1,dtype=np.float32)*alpha
 return Image.fromarray(np.clip(arr+.5,0,255).astype('uint8'))
records=[]
for f in frames:
 target=out/f'frame_{f:04d}.png'
 if f<=76:src=path('hero',f);shutil.copy2(src,target);mode='hero_only';alpha=0.
 elif f<=105:
  x=float(np.clip((f-83)/(95-83),0,1));alpha=x*x*(3-2*x);mix(path('hero',f),path('local',f),alpha).save(target);mode='reveal_local'
 elif f<=195:src=path('local',f);shutil.copy2(src,target);mode='local_only';alpha=1.
 elif f<=240:
  x=float(np.clip((f-211)/(226-211),0,1));alpha=x*x*(3-2*x);mix(path('local',f),path('all',f),alpha).save(target);mode='reveal_formation'
 else:src=path('all',f);shutil.copy2(src,target);mode='full_scene';alpha=1.
 records.append(dict(frame=f,mode=mode,reveal_alpha=alpha,sha256=sha(target)))
(V/('preview_composition.json' if a.preview else 'composition_manifest.json')).write_text(json.dumps(dict(passed=True,frames=records),indent=2));print('COMPOSED',len(records),flush=True)
