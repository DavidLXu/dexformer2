from dexvideo.paths import stage
from pathlib import Path
import bpy,math,json
from mathutils import Vector,Quaternion
R=(stage('parade') / '');V=R/'v5';(V/'render').mkdir(parents=True,exist_ok=True);(V/'audit').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'v3/render/hero.blend'));s=bpy.context.scene;s.frame_set(1)
original={o.name:o.matrix_world.copy() for o in s.objects if o.name.startswith('000/')};cm=s.camera.matrix_world.copy();lens=s.camera.data.lens
bpy.ops.wm.open_mainfile(filepath=str(R/'v4/render/newton.blend'));s=bpy.context.scene;c=s.camera;a=next(o for o in s.objects if o.name.startswith('000/object'))
s.frame_set(84)
# Freeze each hero node to the original frame, preserving world poses.
for name,m in original.items():
 o=s.objects.get(name)
 if o:
  o.animation_data_clear();o.parent=None;o.matrix_world=m
p0=original[a.name].translation.copy();q0=original[a.name].to_quaternion();scale=original[a.name].to_scale()
c.animation_data_clear();c.data.animation_data_clear();a.animation_data_clear();c.rotation_mode='QUATERNION';a.rotation_mode='QUATERNION'
def smooth(x):
 x=max(0,min(1,x));return x*x*x*(x*(x*6-15)+10)
# Continuous push then follow, with analytic per-frame camera aiming.
for f in range(0,87):
 t=(f-1)/30;release=28/30;u=max(0,t-release);z0=2.15;impact=math.sqrt(2*(z0-p0.z)/9.81)
 if u<impact:z=z0-.5*9.81*u*u
 else:
  b=u-impact;z=p0.z+max(0,.65*b-4.905*b*b) if b<.65/4.905 else p0.z
 pos=p0.copy();pos.z=z
 a.location=pos;a.rotation_quaternion=Quaternion((0,1,0),.23*math.sin(math.pi*min(1,u/.82)))@q0;a.scale=scale
 a.keyframe_insert('location',frame=f);a.keyframe_insert('rotation_quaternion',frame=f)
 if f<=29:
  k=smooth((f-6)/23)
  eye=Vector((-2.4,-8.6,3.05)).lerp(Vector((-.30,-1.75,2.43)),k)
  target=Vector((-2.5,0,1.9)).lerp(Vector((p0.x,p0.y,2.16)),k);fl=44+8*k
 else:
  k=smooth((f-29)/25)
  eye=Vector((-.30,-1.75,2.43)).lerp(Vector((-.48,-1.22,.39)),k)
  target=pos+Vector((0,0,.018));fl=52-4*k
  # Settled apple then continuous pullback, ending at exactly original camera.
  if f>=57:
   k=smooth((f-57)/27);eye=eye.lerp(cm.translation,k)
   tracking=(target-eye).to_track_quat('-Z','Y');q=tracking.slerp(cm.to_quaternion(),k);fl=48+(lens-48)*k
  else:q=(target-eye).to_track_quat('-Z','Y')
 if f<=29:q=(target-eye).to_track_quat('-Z','Y')
 c.location=eye;c.rotation_quaternion=q;c.data.lens=fl
 c.keyframe_insert('location',frame=f);c.keyframe_insert('rotation_quaternion',frame=f);c.data.keyframe_insert('lens',frame=f)
for o in [a,c,c.data]:
 for fc in o.animation_data.action.fcurves:
  for kp in fc.keyframe_points:kp.interpolation='LINEAR'
# Remove tree shadows in the tight apple shot, long before the ground is visible.
for o in s.objects:
 if o.type in {'MESH','CURVE'} and not o.name.startswith('000/') and 'studio' not in o.name.lower():
  if o.name.startswith(('tree_','Featured','Fruiting','Apple stem')):
   for f,v in [(1,True),(27,True),(28,False),(86,False)]:o.visible_shadow=v;o.keyframe_insert('visible_shadow',frame=f)
   # Remove secondary ray effects too once canopy is above/outside the view.
   for f,v in [(1,False),(42,False),(43,True),(86,True)]:o.hide_render=v;o.keyframe_insert('hide_render',frame=f)
for o in s.objects:
 if o.type=='MESH' and o.name.startswith('000/') and o!=a:
  for f,v in [(1,True),(27,True),(28,False),(86,False)]:o.hide_render=v;o.keyframe_insert('hide_render',frame=f)
s.frame_set(84);bpy.context.view_layer.update()
errs={name:max(abs(s.objects[name].matrix_world[i][j]-m[i][j]) for i in range(4) for j in range(4)) for name,m in original.items() if name in s.objects}
assert max(errs.values())<1e-5,max(errs.values())
camerr=max(abs(c.matrix_world[i][j]-cm[i][j]) for i in range(4) for j in range(4));assert camerr<1e-5
(V/'audit/join.json').write_text(json.dumps(dict(passed=True,hero_world_transform_error=max(errs.values()),camera_error=camerr,apple_world_position=list(a.matrix_world.translation),shadow_disabled_frame=28,no_crossfade=True),indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(V/'render/newton.blend'))
