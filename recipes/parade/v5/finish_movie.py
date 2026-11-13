from dexvideo.paths import stage
from pathlib import Path
import subprocess,json,hashlib,shutil
from PIL import Image
import imageio_ffmpeg
R=(stage('parade') / '');V=R/'v5';frames=V/'frames';frames.mkdir(exist_ok=True)
assert len(list((V/'intro_frames').glob('frame_*.png')))==84
for f in range(1,85):
 p=V/'intro_frames'/f'frame_{f:04d}.png'
 im=Image.open(p);assert im.size==(1920,1080)
 im.save(frames/f'frame_{f:04d}.png')
for f in range(1,361):shutil.copy2(R/'v3/frames'/f'frame_{f:04d}.png',frames/f'frame_{f+84:04d}.png')
ff=imageio_ffmpeg.get_ffmpeg_exe();out=V/'DexFormer_2.0_Newton_14p8s_v5.mp4'
subprocess.run([ff,'-y','-framerate','30','-start_number','1','-i',str(frames/'frame_%04d.png'),'-loop','1','-framerate','30','-i',str(R/'v3/title.png'),'-filter_complex','[1:v]format=rgba,fade=t=in:st=12.95:d=0.35:alpha=1[title];[0:v][title]overlay=0:0:shortest=1,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[v]','-map','[v]','-t','14.8','-r','30','-c:v','libx264','-preset','slow','-crf','17','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart',str(out)],check=True)
n,t=imageio_ffmpeg.count_frames_and_secs(str(out));assert n==444 and abs(t-14.8)<.05
for f in range(1,361):assert (frames/f'frame_{f+84:04d}.png').read_bytes()==(R/'v3/frames'/f'frame_{f:04d}.png').read_bytes()
(V/'audit/COMPLETE.json').write_text(json.dumps(dict(passed=True,frames=n,seconds=t,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),policy_source_frames_unchanged=360,animated_prologue_frames=84),indent=2))
print('COMPLETE',out,flush=True)
