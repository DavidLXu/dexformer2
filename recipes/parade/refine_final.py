from dexvideo.paths import stage
from pathlib import Path
import bpy,json
from mathutils import Vector
R=(stage('parade') / '');bpy.ops.wm.open_mainfile(filepath=str(R/'render/parade.blend'));s=bpy.context.scene
for o in bpy.data.objects:
 idx=int(o.name[:3]) if o.name[:3].isdigit() else -1
 if idx not in [2,3] or not o.animation_data or not o.animation_data.action:continue
 delta={2:-48,3:-52}[idx]
 for f in o.animation_data.action.fcurves:
  for k in f.keyframe_points:
   if 1<k.co.x<420:k.co.x+=delta
  f.update()
cam=s.camera;data=cam.data
for frame,loc,target in [(171,(2.,-3.5,3.4),(0,.4,.4)),(219,(1.9,-3.6,3.5),(0,.4,.4))]:
 cam.location=loc;cam.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler();cam.keyframe_insert('location',frame=frame);cam.keyframe_insert('rotation_euler',frame=frame);data.lens=50;data.keyframe_insert('lens',frame=frame);data.dof.focus_distance=(Vector(target)-Vector(loc)).length;data.keyframe_insert('dof.focus_distance',frame=frame)
a=json.loads((R/'render/trajectory_audit.json').read_text());a['entries'][2]['start_movie_frame']=80;a['entries'][3]['start_movie_frame']=90;(R/'render/trajectory_audit.json').write_text(json.dumps(a,indent=2))
s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(R/'render/parade.blend'))
(R/'benchmark').mkdir(exist_ok=True)
for f in (R/'frames').glob('frame_*.png'):f.rename(R/'benchmark'/f.name)
