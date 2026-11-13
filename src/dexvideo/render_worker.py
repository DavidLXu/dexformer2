"""Short-lived native Blender worker; explicit device selection and valid-frame reuse."""
from pathlib import Path
import argparse,math,json,time,os
import bpy
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('--blend',required=True);p.add_argument('--out',required=True);p.add_argument('--frames',required=True);p.add_argument('--fps',type=int,default=30);p.add_argument('--scale',type=int,default=100);p.add_argument('--samples',type=int,default=24);p.add_argument('--device',choices=['CPU','OPTIX','CUDA','METAL'],default='CPU');a=p.parse_args()
bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve()));s=bpy.context.scene
s.cycles.use_persistent_data=False;s.render.threads_mode='FIXED';s.render.threads=4
if a.device=='CPU':s.cycles.device='CPU'
else:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type=a.device;prefs.get_devices()
    selected=[d for d in prefs.devices if d.type==a.device]
    if not selected:raise RuntimeError(f'No {a.device} device available; use --device CPU')
    for d in prefs.devices:d.use=d in selected
    s.cycles.device='GPU'
s.render.resolution_percentage=a.scale;s.cycles.samples=a.samples
out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
settings=dict(blend_sha256=__import__('hashlib').sha256(Path(a.blend).read_bytes()).hexdigest(),fps=a.fps,scale=a.scale,samples=a.samples,device=a.device)
settings_path=out/'render_settings.json'
if settings_path.exists() and json.loads(settings_path.read_text())!=settings:raise RuntimeError('Output settings differ; choose another output directory')
settings_path.write_text(json.dumps(settings,indent=2))
w=round(s.render.resolution_x*a.scale/100);h=round(s.render.resolution_y*a.scale/100)
for f in map(int,a.frames.split(',')):
    dest=out/f'frame_{f:04d}.png'
    if dest.exists():
        try:
            with Image.open(dest) as im:assert im.size==(w,h);im.verify()
            continue
        except Exception:dest.rename(dest.with_suffix('.partial'))
    native=1+(f-1)*s.render.fps/a.fps
    s.frame_set(math.floor(native),subframe=native-math.floor(native));tmp=out/f'.frame_{f:04d}.png'
    s.render.filepath=str(tmp);bpy.ops.render.render(write_still=True)
    with Image.open(tmp) as im:
        rgba=im.convert('RGBA');Image.alpha_composite(Image.new('RGBA',rgba.size,'white'),rgba).convert('RGB').save(tmp)
    tmp.replace(dest);print('FRAME_DONE',f,flush=True)
