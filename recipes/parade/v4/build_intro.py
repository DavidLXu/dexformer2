from dexvideo.paths import stage
"""A native 3-D Newton prologue; the existing real-policy film remains unchanged."""
from pathlib import Path
import bpy,math,json,random
from mathutils import Vector,Quaternion
R=(stage('parade') / '');V=R/'v4'
bpy.ops.wm.open_mainfile(filepath=str(R/'v3/render/hero.blend'))
s=bpy.context.scene;s.frame_set(1);cam=s.camera
hero_camera=cam.matrix_world.copy();hero_lens=cam.data.lens
# Freeze only this new prologue scene at the original first frame.
for o in list(s.objects):
 if o.type=='MESH' and o.hide_render:
  bpy.data.objects.remove(o,do_unlink=True)
for o in list(s.objects):
 basis=o.matrix_basis.copy();o.animation_data_clear();o.matrix_basis=basis
 if o.data and hasattr(o.data,'animation_data_clear'):o.data.animation_data_clear()
apple=next(o for o in s.objects if o.name.startswith('000/object'))
end=apple.matrix_world.copy();apple.parent=None;apple.matrix_world=end
p0=end.translation.copy();q0=end.to_quaternion();hero_meshes=[o for o in s.objects if o.type=='MESH' and o.name.startswith('000/') and o!=apple]
# Append the photographed/textured tree with its original materials.
with bpy.data.libraries.load(str(V/'assets/tree_small_02_2k.blend'),link=False) as (a,b):
 b.objects=[n for n in a.objects if n in ['tree_small_02_LOD0','tree_small_02_leaves_a_LOD0']]
new=[o for o in b.objects if o]
for o in new:o.hide_render=o.name!='tree_small_02_LOD0';o.hide_viewport=False
for o in new:
 if not o.users_collection:s.collection.objects.link(o)
for im in bpy.data.images:
 if 'tree_small_02' in im.name:
  p=V/'assets/textures'/Path(im.filepath).name
  if p.exists():im.filepath=str(p);im.reload()
# The asset's render objects are identified in the separate inventory audit.
trees=[o for o in new if o.type=='MESH' and not o.hide_render]
parent=bpy.data.objects.new('Newton tree placement',None);s.collection.objects.link(parent)
for o in new:
 if o.type in {'CAMERA','LIGHT'}:
  o.hide_render=True
 elif o.parent is None:
  o.parent=parent
parent.location=(-2.95,.10,0);parent.rotation_euler[2]=math.radians(65);parent.scale=(.77,.77,.77)
# An unobtrusive extra fruiting twig reaches the featured apple.
mat=bpy.data.materials.new('Fruiting twig bark');mat.diffuse_color=(.12,.065,.024,1);mat.use_nodes=True
bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.12,.065,.024,1);bs.inputs['Roughness'].default_value=.85
noise=mat.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=55
bump=mat.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.25;bump.inputs['Distance'].default_value=.015
mat.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);mat.node_tree.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
def twig(name,points,radius):
 c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=16;c.bevel_depth=radius;c.bevel_resolution=3
 sp=c.splines.new('BEZIER');sp.bezier_points.add(len(points)-1)
 for i,(bp,co) in enumerate(zip(sp.bezier_points,points)):
  bp.co=co;bp.handle_left_type=bp.handle_right_type='AUTO';bp.radius=max(.15,1-i/(len(points)+.1))
 ob=bpy.data.objects.new(name,c);s.collection.objects.link(ob);c.materials.append(mat);return ob
zstart=2.15
branch=twig('Featured fruiting branch',[(-2.55,.10,2.35),(-1.95,-.10,2.52),(-1.30,-.34,2.38),(p0.x,p0.y,zstart+.10)],.018)
stem=twig('Apple stem',[(p0.x,p0.y,zstart+.10),(p0.x+.003,p0.y,zstart+.045)],.0024)
leaf_template=next(o for o in new if o.name=='tree_small_02_leaves_a_LOD0')
for i in range(12):
 u=i/12;x=-1.9+u*1.05;y=-.13-u*.4;z=2.51-u*.24
 ob=bpy.data.objects.new('Fruiting twig leaves '+str(i),leaf_template.data);s.collection.objects.link(ob)
 ob.location=(x,y,z);ob.rotation_euler=(.3*math.sin(i),.6*math.cos(i),i*2.4);ob.scale=(.6,.6,.6)

# Small fruit accents use the same scan, with restrained scale variation.
rng=random.Random(42)
for i,loc in enumerate([(-2.0,-.55,2.65),(-3.65,-.5,2.4),(-2.5,-.92,2.0),(-3.4,.3,3.0),(-1.7,.0,3.0),(-3.0,-.5,3.35),(-2.4,.65,2.75)]):
 o=bpy.data.objects.new('Canopy apple '+str(i),apple.data);s.collection.objects.link(o);o.location=loc;o.rotation_mode='QUATERNION';o.rotation_quaternion=q0;o.scale=(1,1,1)
# Animate apple: hold, gravitational acceleration, small dissipating bounce, settle.
# Animated prologue only. The policy trajectory after the join is never edited.
for f in range(1,85):
 t=(f-1)/30
 fall=max(0,t-1.05);height=zstart-.5*9.81*fall*fall
 impact=1.05+math.sqrt(2*(zstart-p0.z)/9.81)
 if t<impact:z=max(p0.z,height)
 else:
  u=t-impact
  z=p0.z+max(0,.9*u-4.905*u*u) if u<.9/4.905 else p0.z
 pos=p0.copy();pos.z=z
 apple.location=pos;apple.rotation_mode='QUATERNION'
 # Return precisely to the recorded orientation by the last close-up.
 k=min(1,max(0,(t-1.05)/.85));spin=.32*math.sin(math.pi*k)
 apple.rotation_quaternion=Quaternion((0,1,0),spin)@q0
 apple.keyframe_insert('location',frame=f);apple.keyframe_insert('rotation_quaternion',frame=f)
# Film camera: whole tree, branch insert, tracking fall, final exact match.
def aim(frame,eye,target,lens):
 cam.location=eye;cam.rotation_mode='QUATERNION';cam.rotation_quaternion=(Vector(target)-Vector(eye)).to_track_quat('-Z','Y');cam.data.lens=lens
 cam.keyframe_insert('location',frame=frame);cam.keyframe_insert('rotation_quaternion',frame=frame);cam.data.keyframe_insert('lens',frame=frame)
keys=[(1,(-2.4,-8.6,3.05),(-2.5,0,1.9),44),(23,(-2.25,-8.1,3.0),(-2.45,0,1.9),44),
 (24,(-.30,-2.20,2.50),(p0.x,p0.y,2.18),62),(32,(-.30,-2.15,2.46),(p0.x,p0.y,2.15),62),
 (42,(-.25,-2.1,2.1),(p0.x,p0.y,1.7),56),(51,(-.37,-1.65,.93),(p0.x,p0.y,.55),52),
 (57,(-.48,-1.22,.39),(p0.x,p0.y,.10),48),(62,(-.48,-1.22,.39),(p0.x,p0.y,.10),48)]
for k in keys:aim(*k)
cam.location=hero_camera.translation;cam.rotation_quaternion=hero_camera.to_quaternion();cam.data.lens=hero_lens
for f in [84,85]:
 cam.keyframe_insert('location',frame=f);cam.keyframe_insert('rotation_quaternion',frame=f);cam.data.keyframe_insert('lens',frame=f)
# Smooth trajectory except deliberate branch cut at frame 24.
for obj in [cam,cam.data]:
 for fc in obj.animation_data.action.fcurves:
  for kp in fc.keyframe_points:
   kp.interpolation='BEZIER';kp.handle_left_type=kp.handle_right_type='AUTO_CLAMPED'
   if int(kp.co.x)==23:kp.interpolation='CONSTANT'
for ob in [apple]:
 for fc in ob.animation_data.action.fcurves:
  for kp in fc.keyframe_points:kp.interpolation='LINEAR'
# Reveal the single arm as the ground-level shot pulls out; no other robots.
for o in hero_meshes:
 for f,hide in [(1,True),(23,True),(24,False),(85,False)]:
  o.hide_render=hide;o.keyframe_insert('hide_render',frame=f)
# A minute canopy sway; the trunk base remains fixed.
base=parent.rotation_euler.copy()
for f in range(1,86,4):
 parent.rotation_euler=base.copy();parent.rotation_euler[1]=.0015*math.sin(f*.09);parent.keyframe_insert('rotation_euler',frame=f)

for ob in list(s.objects):
 if ob.name.startswith('Canopy apple'):bpy.data.objects.remove(ob,do_unlink=True)
cam.data.dof.use_dof=False
s.frame_start=1;s.frame_end=85;s.render.resolution_percentage=100;s.cycles.samples=64;s.cycles.transparent_max_bounces=12;s.cycles.use_persistent_data=True
s.render.image_settings.color_mode='RGBA';s.render.film_transparent=True;s.use_nodes=False
s.camera=cam;s.frame_set(84)
bpy.context.view_layer.update()
err=max(abs(cam.matrix_world[i][j]-hero_camera[i][j]) for i in range(4) for j in range(4))
(V/'audit').mkdir(exist_ok=True);(V/'render').mkdir(exist_ok=True)
(V/'audit/scene_build.json').write_text(json.dumps(dict(apple_landing=list(p0),camera_join_max_abs_error=err,tree_source='https://polyhaven.com/a/tree_small_02',tree_objects=[o.name for o in trees],intro_frames=84,full_duration_s=14.8,staged_fall=True,policy_sequence_unchanged=True),indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(V/'render/newton.blend'))
print('BUILD_DONE',err,flush=True)
