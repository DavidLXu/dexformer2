from pathlib import Path
import json,hashlib,subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.interpolate import PchipInterpolator
import imageio_ffmpeg
from dexvideo.paths import stage
import argparse
p=argparse.ArgumentParser();p.add_argument('video',type=Path);p.add_argument('--output',type=Path);args=p.parse_args()
R=stage('packing_speed');S=stage('packing')
R.joinpath('overlays').mkdir(exist_ok=True);R.joinpath('audit').mkdir(exist_ok=True)
sel=json.loads((S/'selection.json').read_text());layout=json.loads((S/'audit/layout.json').read_text())
source=args.video.resolve()
n,seconds=imageio_ffmpeg.count_frames_and_secs(str(source));assert n==900 and abs(seconds-30)<.05, 'Requires the 30fps/30s packing film and its matching layout audit'
# Original recording summaries declare a 1/60-second control timestep.
arms={'franka':'Franka','flexiv':'Flexiv','kuka':'KUKA','xarm':'xArm7'}
hands={'revo3':'Revo3','sharpa':'Sharpa','leap':'LEAP','allegro':'Allegro','rapid':'RAPID','shadow':'Shadow'}
curves=[]
for i,(c,rec) in enumerate(zip(sel['clips'],layout['records'])):
 assert c['pair']==rec['pair']
 lift=next(e['step'] for e in c['row']['events'] if e['to_state']==2)
 for ev in rec['events']:
  tt=[ev['begin'],ev['begin']+ev['grasp_duration'],ev['release'],ev['settled'],ev['end']]
  ss=[rec['source_start'],lift,rec['source_release'],rec['source_settled'],rec['source_end']]
  curves.append(dict(station=i,box=ev['box'],pair=c['pair'],event=ev,map=PchipInterpolator(tt,ss)))
lead=[x for x in curves if x['box']==0]
# Average actual source-time advance over this output frame, no aesthetic easing.
def speed(c,t):
 e=c['event'];a=max(t,e['begin']);b=min(t+1/30,e['end'])
 return float((c['map'](b)-c['map'](a))/60/(b-a)) if b>a else None
def portable_font(size,bold=False):
 for file in (["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if bold else ["/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]):
  if Path(file).exists():return ImageFont.truetype(file,size)
 return ImageFont.load_default(size=size)
font=portable_font(34,True);small=portable_font(17);number_range=portable_font(30,True)
manifest=[]
for f in range(900):
 t=f/30
 if t<25.5:
  c=next((x for x in lead if t<x['event']['settled']),lead[-1]);rate=speed(c,t) if t>=c['event']['begin'] else None
  arm,hand=c['pair'].split('_');detail=f'{arms[arm]} + {hands[hand]}'
  value=f'{rate:.1f}×' if rate is not None else 'Waiting'
  entry=dict(frame=f+1,time=t,scope='lead_box_station',station=c['station'],pair=c['pair'],box=0,speed=rate)
 else:
  active=[(c,speed(c,t)) for c in curves if c['event']['begin']<=t<c['event']['end']]
  rates=[v for _,v in active];lo=min(rates);hi=max(rates)
  value=f'{lo:.1f}–{hi:.1f}×';detail='All active stations'
  entry=dict(frame=f+1,time=t,scope='all_active_replayed_actions',speed_min=lo,speed_max=hi,actions=[dict(station=c['station'],box=c['box'],speed=v) for c,v in active])
 entry.update(display=value,detail=detail);manifest.append(entry)
 im=Image.new('RGBA',(258,100));d=ImageDraw.Draw(im)
 d.rounded_rectangle((0,0,257,99),radius=10,fill=(255,255,255,125),outline=(86,102,112,22),width=1)
 d.text((18,10),'Action replay',font=small,fill=(66,79,88,180))
 d.text((18,30),value,font=number_range if '–' in value else font,fill=(51,67,78,215))
 d.text((18,76),detail,font=small,fill=(66,79,88,190))
 im.save(R/'overlays'/f'{f+1:04d}.png')
(R/'audit/speed_per_frame.json').write_text(json.dumps(manifest,indent=2))
(R/'audit/method.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_control_dt=1/60,output_fps=30,formula='Source-time increment / output-time increment on each frame; clipped to active replay interval at boundaries',display_precision=0.1,scope='Current lead-box deposit station until25.5s; range of all active trajectory replays from25.5s onward',not_global_speed=True,scripted_transport_and_camera_excluded=True,original_film_unchanged=True),indent=2))
ff=imageio_ffmpeg.get_ffmpeg_exe();out=args.output or R/'order-packing-speed.mp4'
subprocess.run([ff,'-y','-i',str(source),'-framerate','30','-i',str(R/'overlays/%04d.png'),'-filter_complex','[0:v][1:v]overlay=x=W-w-46:y=H-h-38:shortest=1:format=auto,format=yuv420p[v]','-map','[v]','-c:v','libx264','-preset','slow','-crf','16','-threads','8','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart',str(out)],check=True)
print(out)
