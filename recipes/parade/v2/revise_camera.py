from dexvideo.paths import stage
from pathlib import Path
import bpy,json,shutil,hashlib,math
from mathutils import Vector
R=(stage('parade') / '');V=R/'v2';(V/'render').mkdir(parents=True,exist_ok=True);(V/'frames').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'render/parade.blend'));s=bpy.context.scene;cam=s.camera;data=cam.data
# Preserve the exact sampled opening camera, including the outbound tangent.
opening=[]
for f in range(1,78):
 s.frame_set(f);opening.append((f,cam.location.copy(),cam.rotation_euler.copy(),data.lens,data.dof.focus_distance))
cam.animation_data_clear();data.animation_data_clear()
for f,loc,rot,lens,focus in opening:
 cam.location=loc;cam.rotation_euler=rot;cam.keyframe_insert('location',frame=f);cam.keyframe_insert('rotation_euler',frame=f);data.lens=lens;data.keyframe_insert('lens',frame=f);data.dof.focus_distance=focus;data.keyframe_insert('dof.focus_distance',frame=f)
keys=[(106,(0,-3.8,3.3),(0,.4,.40),50),(165,(0,-3.9,3.35),(0,.4,.40),50),
(195,(0,-4.1,3.5),(0,.5,.40),49),(245,(0,-10.2,10.5),(0,3.5,.35),45),
(293,(0,-15.5,17.5),(0,4.8,.35),43),(360,(0,-16.,18.),(0,4.8,.35),43)]
for f,loc,target,lens in keys:
 cam.location=loc;cam.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler();cam.keyframe_insert('location',frame=f);cam.keyframe_insert('rotation_euler',frame=f);data.lens=lens;data.keyframe_insert('lens',frame=f);data.dof.focus_distance=(Vector(target)-Vector(loc)).length;data.keyframe_insert('dof.focus_distance',frame=f)
for block in [cam,data]:
 for curve in block.animation_data.action.fcurves:
  for key in curve.keyframe_points:
   key.interpolation='LINEAR' if key.co.x<77 else 'BEZIER';key.handle_left_type='AUTO_CLAMPED';key.handle_right_type='AUTO_CLAMPED'
# Fit the shorter 12s edit by starting only background rollouts 60 frames earlier.
# This moves complete clips in time; q and object motion retain their original 1x speed.
for o in bpy.data.objects:
 idx=int(o.name[:3]) if o.name[:3].isdigit() else -1
 if idx<4 or not o.animation_data or not o.animation_data.action:continue
 for c in o.animation_data.action.fcurves:
  for k in c.keyframe_points:
   if k.co.x>1:k.co.x-=60
  c.update()
s.frame_end=360;s.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(V/'render/parade.blend'))
records=[]
for f in range(1,77):
 src=R/'frames'/f'frame_{f:04d}.png';dst=V/'frames'/src.name
 if src.exists():
  shutil.copy2(src,dst);records.append(dict(frame=f,sha256=hashlib.sha256(dst.read_bytes()).hexdigest()))
shutil.copy2(R/'title.png',V/'title.png')
a=json.loads((R/'render/trajectory_audit.json').read_text())
for e in a['entries']:
 if e['index']>=4:e['start_movie_frame']-=60
(V/'render/trajectory_audit.json').write_text(json.dumps(a,indent=2))
# The camera has no sideways view or roll once the middle local shot settles.
for f in range(106,361):
 s.frame_set(f);right=cam.matrix_world.to_3x3()@Vector((1,0,0));assert abs(right.y)<1e-5 and abs(right.z)<1e-5,(f,list(right));assert abs(cam.location.x)<1e-5
(V/'revision.json').write_text(json.dumps(dict(duration_s=12,frames=360,preserved_opening_frames=records,changes=['One centered local view replaces the two/four-step reveals','Centered axial pullback, no sideways yaw or camera roll after frame106','Background clips shifted earlier60frames, no trajectory deformation'],camera_axis_verified_frames=[106,360]),indent=2))
print('REVISION_READY',flush=True)
