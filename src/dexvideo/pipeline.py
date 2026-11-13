from pathlib import Path
import subprocess,sys,os,json
import imageio_ffmpeg
from PIL import Image
from .paths import REPO,stage
from .assets import initialize,missing_assets,sha
SCENES={
 'conveyor':dict(stages=[('conveyor','build_scene.py')],root='conveyor',blend='conveyor.blend',seconds=14.8,fps=30,logo=13.1,fade=.4),
 'ring':dict(stages=[('ring','build_scene.py'),('ring','validate_pacing.py')],root='ring',blend='ring.blend',seconds=15,fps=60,logo=13.4,fade=.6),
 'long-table':dict(stages=[('table_base','build.py'),('table_objects','build.py'),('table','patch_camera.py')],root='table',blend='table.blend',seconds=15,fps=60,logo=12.5666666667,fade=.6),
 'order-packing':dict(stages=[('packing','build.py'),('packing','audit_native.py')],root='packing',blend='packing.blend',seconds=30,fps=30,logo=28.6,fade=.6,logo_y=-180),
 'newton':dict(stages=[('parade','build_movie.py'),('parade','art_direction.py'),('parade','refine_final.py'),('parade/v2','revise_camera.py'),('parade/v3','prepare_reveal.py'),('parade/v4','build_intro.py'),('parade/v5','build_v5.py')],root='parade/v5',blend='newton.blend',seconds=14.8,fps=30,logo=12.95,fade=.35),
 'apples':dict(stages=[('apples','build.py')],root='apples',blend='{index}.blend',seconds=3,fps=30),
}
def run_recipe(folder,name,args=()):
    for sub in ['audit','render','frames']:(stage(folder)/sub).mkdir(exist_ok=True)
    subprocess.run([sys.executable,str(REPO/'recipes'/folder/name),*map(str,args)],check=True)
def build(name,index=0):
    initialize();missing=missing_assets(tree=name=='newton')
    if missing:raise RuntimeError(f'{len(missing)} external asset files missing. Run dexvideo import-assets and (for Newton) dexvideo fetch-tree. See docs/assets.md.')
    for folder,script in SCENES[name]['stages']:run_recipe(folder,script,['--index',index] if name=='apples' else [])
def config(name,index=0):
    c=dict(SCENES[name]);c['blend']=c['blend'].format(index=index)
    if name=='apples':
        a=json.loads((stage('apples')/'audit'/f'{index}.json').read_text());c['seconds']=a['seconds'];c['pair']=a['pair']
    return c

def render_job(blend,out,frames,fps=30,device='CPU',scale=100,samples=24,batch=8):
    for k in range(0,len(frames),batch):
        subprocess.run([sys.executable,'-m','dexvideo.render_worker','--blend',str(blend),'--out',str(out),'--frames',','.join(map(str,frames[k:k+batch])),'--fps',str(fps),'--device',device,'--scale',str(scale),'--samples',str(samples)],check=True)
def render(name,index=0,preview=False,frames=None,device='CPU',samples=24,batch=8):
    c=config(name,index);r=stage(c['root']);out=r/('preview' if preview else 'frames')
    if name=='apples':out=out/str(index)
    fps=c['fps'];kwargs=dict(device=device,scale=25 if preview else 100,samples=min(samples,4) if preview else samples,batch=batch)
    if name=='newton' and not preview:
        if frames:raise ValueError('Newton full render assembles several layers; omit --frames or use --preview')
        render_job(r/'render/newton.blend',r/'intro_frames',list(range(1,85)),30,**kwargs)
        for blend,folder,ff in [('hero','layers/hero',range(1,106)),('local','layers/local',range(77,241))]:
            render_job(stage('parade/v3')/f'render/{blend}.blend',stage('parade/v3')/folder,list(ff),30,**kwargs)
        render_job(stage('parade/v2')/'render/parade.blend',stage('parade/v2')/'frames',list(range(196,361)),30,**kwargs)
        run_recipe('parade/v3','compose_reveal.py');return
    chosen=frames or ([1] if preview else list(range(1,round(c['seconds']*fps)+1)))
    limit=84 if name=='newton' else round(c['seconds']*fps)
    if not chosen or min(chosen)<1 or max(chosen)>limit:raise ValueError(f'Frame indices must be 1..{limit}')
    render_job(r/'render'/c['blend'],out,chosen,fps,**kwargs)
def encode(name,index=0):
    if name=='newton':run_recipe('parade/v5','finish_movie.py');return
    c=config(name,index);r=stage(c['root']);frames=r/'frames';n=round(c['seconds']*c['fps'])
    if name=='apples':frames=frames/str(index)
    for f in range(1,n+1):
        with Image.open(frames/f'frame_{f:04d}.png') as im:im.verify()
    out=r/(f'apple_{c["pair"]}_0.5x.mp4' if name=='apples' else f'{name}.mp4');ff=imageio_ffmpeg.get_ffmpeg_exe()
    command=[ff,'-y','-framerate',str(c['fps']),'-i',str(frames/'frame_%04d.png')]
    if 'logo' in c:
        command+=['-loop','1','-framerate',str(c['fps']),'-i',str(REPO/'branding/title.png'),'-filter_complex',f"[1:v]format=rgba,fade=t=in:st={c['logo']}:d={c['fade']}:alpha=1[t];[0:v][t]overlay=0:{c.get('logo_y',0)}:shortest=1,format=yuv420p[v]",'-map','[v]']
    command+=['-t',str(c['seconds']),'-c:v','libx264','-preset','slow','-crf','17','-threads','8','-pix_fmt','yuv420p','-movflags','+faststart',str(out)]
    subprocess.run(command,check=True)
    count,seconds=imageio_ffmpeg.count_frames_and_secs(str(out));assert count==n and abs(seconds-c['seconds'])<.05
    subprocess.run([ff,'-v','error','-i',str(out),'-f','null','-'],check=True)
    (r/f'COMPLETE_{index if name=="apples" else name}.json').write_text(json.dumps(dict(passed=True,frames=count,seconds=seconds,sha256=sha(out)),indent=2));print(out)
