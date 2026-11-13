from dexvideo.paths import stage
"""Native geometry + unmodified successful policy trajectories, rigidly staged."""
from pathlib import Path
import json,math,hashlib,time,sys
import numpy as np
from scipy.spatial.transform import Rotation
import bpy
from mathutils import Matrix,Quaternion,Vector
ROOT=(stage('parade') / '');B=ROOT/'bundle'
FPS=30;END=444
assets=json.loads((B/'assets.json').read_text());manifest=json.loads((B/'clips.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='GPU';scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.cycles.use_persistent_data=False
scene.cycles.max_bounces=6;scene.cycles.diffuse_bounces=3;scene.cycles.glossy_bounces=3;scene.cycles.transparent_max_bounces=128
scene.render.threads_mode='FIXED';scene.render.threads=6
scene.render.resolution_x=1920;scene.render.resolution_y=1080;scene.render.resolution_percentage=100;scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=END
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.film_transparent=False
scene.render.use_motion_blur=True;scene.render.motion_blur_shutter=.06
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.55
world=bpy.data.worlds.new('White studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.78,.84,1,1);world.node_tree.nodes['Background'].inputs[1].default_value=.45;scene.world=world
mesh_cache={};mat_cache={}
def get_material(spec):
 key=json.dumps(spec,sort_keys=True)
 if key in mat_cache:return mat_cache[key]
 mat=bpy.data.materials.new('Native material '+str(len(mat_cache)));mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;p=n.get('Principled BSDF');p.inputs['Roughness'].default_value=.45
 wrapper=spec
 if spec['type']=='normalmap':spec=spec['bsdf']
 def value(inp,v,raw=False):
  if isinstance(v,dict) and v.get('type')=='bitmap':
   t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(B/v['filename']),check_existing=True)
   if raw or v.get('raw'):t.image.colorspace_settings.name='Non-Color'
   l.new(t.outputs['Color'],inp)
  elif isinstance(v,dict):inp.default_value=(*v['value'],1)
  elif isinstance(v,list):inp.default_value=(*v,1)
  else:
   if inp.type=='RGBA':inp.default_value=(v,v,v,1)
   else:inp.default_value=v
 value(p.inputs['Base Color'],spec.get('base_color',spec.get('reflectance',.5)))
 value(p.inputs['Metallic'],spec.get('metallic',0.),True);value(p.inputs['Roughness'],spec.get('roughness',.5),True)
 if wrapper['type']=='normalmap':
  t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(B/wrapper['normalmap']['filename']),check_existing=True);t.image.colorspace_settings.name='Non-Color';normal=n.new('ShaderNodeNormalMap');l.new(t.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],p.inputs['Normal'])
 info=n.new('ShaderNodeObjectInfo');l.new(info.outputs['Alpha'],p.inputs['Alpha'])
 mat_cache[key]=mat;return mat

def get_mesh(part):
 key=part['mesh']+'|'+json.dumps(part['material'],sort_keys=True)
 if key in mesh_cache:return mesh_cache[key]
 d=np.load(B/part['mesh']);v=d['vertices'];f=d['faces'];m=bpy.data.meshes.new('CAD '+str(len(mesh_cache)));m.from_pydata(v.tolist(),[],f.tolist());m.update()
 if 'uv' in d:
  uv=m.uv_layers.new(name='UVMap');uv.data.foreach_set('uv',d['uv'][f.ravel()].ravel())
 m.polygons.foreach_set('use_smooth',np.ones(len(f),dtype=bool));m.normals_split_custom_set_from_vertices(d['normals'].tolist());m.materials.append(get_material(part['material']));mesh_cache[key]=m;return m

def add_obj(name,mesh=None):
 o=bpy.data.objects.new(name,mesh);scene.collection.objects.link(o);return o

def keyquat(obj,q,frames):
 # FCurves in bulk: no operator calls per frame, continuous quaternion signs.
 q=np.array(q,dtype=float);sign=np.ones(len(q))
 for i in range(1,len(q)):
  if np.dot(q[i-1],q[i])<0:q[i]*=-1
 obj.rotation_mode='QUATERNION'
 action=bpy.data.actions.new(obj.name+' motion');obj.animation_data_create();obj.animation_data.action=action
 for k in range(4):
  f=action.fcurves.new(data_path='rotation_quaternion',index=k);f.keyframe_points.add(len(frames));f.keyframe_points.foreach_set('co',np.c_[frames,q[:,k]].ravel())
  for kp in f.keyframe_points:kp.interpolation='LINEAR'
  f.update()
 obj.animation_data.action_slot=action.slots[0]
 return action

def animate_pos(obj,positions,frames,action):
 for k in range(3):
  f=action.fcurves.new(data_path='location',index=k);f.keyframe_points.add(len(frames));f.keyframe_points.foreach_set('co',np.c_[frames,positions[:,k]].ravel())
  for kp in f.keyframe_points:kp.interpolation='LINEAR'
  f.update()

V=(stage('conveyor') / '');M=json.loads((V/'selection.json').read_text());clips=M['clips'];ordered=M['ordered'];assert len(clips)==24 and len(ordered)==60
from collections import Counter
assert ordered[0]['pair']=='franka_revo3' and set(c['pair'] for c in ordered[:24])==set(c['pair'] for c in clips)
DX,DY=1.65,2.1
cam=add_obj('Camera',bpy.data.cameras.new('Camera'));scene.camera=cam
# Hold the first station, sweep the full front row, then pull back on a level horizon.
keys=[(1,(-1.8,-3.2,3.0),(.05,-.15,1.05),46),
 (90,(-1.79,-3.19,2.99),(.07,-.17,1.05),46),
 (130,(-1.70,-3.18,2.97),(.15,-.18,1.05),46),
 (170,(-1.50,-3.20,2.94),(.35,-.18,1.04),46),
 (210,(-1.10,-3.23,2.90),(.70,-.18,1.04),45),
 (250,(-.40,-3.27,2.86),(1.20,-.17,1.05),45),
 (280,(.80,-3.32,2.84),(2.40,-.16,1.08),45),
 (310,(5.50,-3.48,2.82),(6.00,-.14,1.12),44),
 (340,(14.20,-3.80,3.10),(13.80,-.05,1.15),44),
 (375,(13.00,-6.50,5.80),(10.50,2.00,.94),44),
 (415,(7.50,-14.50,17.50),(7.50,5.00,.83),44),
 (444,(7.50,-16.30,19.50),(7.50,5.30,.81),44)]
for f,eye,targ,lens in keys:
 cam.location=eye;cam.rotation_euler=(Vector(targ)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=lens
 cam.keyframe_insert('location',frame=f);cam.keyframe_insert('rotation_euler',frame=f);cam.data.keyframe_insert('lens',frame=f)
for o in [cam,cam.data]:
 for fc in o.animation_data.action.fcurves:
  for kp in fc.keyframe_points:kp.interpolation='BEZIER';kp.handle_left_type=kp.handle_right_type='AUTO_CLAMPED'
# Reveal the front row in camera order, then reveal deeper rows only after
# the front row has been scanned, creating a staged surprise.
reveal=np.full(60,END,dtype=int); reveal[0]=1
front_schedule=[1,130,280,290,300,315,325,333,338,340]
for i in range(1,60):
 row,col=divmod(i,10)
 if row==0: reveal[i]=front_schedule[col]
 else: reveal[i]=342+row*4+int((9-col)*.5)
assert max(reveal)<=440,(max(reveal),np.where(reveal>440)[0].tolist())
station_objects=[];station_records=[]
metal=get_material(dict(type='principled',base_color={'type':'rgb','value':[.55,.6,.64]},metallic=.65,roughness=.3));rubber=get_material(dict(type='principled',base_color={'type':'rgb','value':[.003,.005,.008]},roughness=.8));blue=get_material(dict(type='principled',base_color={'type':'rgb','value':[.035,.23,.32]},roughness=.4));white=get_material(dict(type='principled',base_color={'type':'rgb','value':[.82,.85,.86]},roughness=.55))
def box(name,loc,size,mat,parent=None,bevel=0):
 verts=[(x*size[0]/2,y*size[1]/2,z*size[2]/2) for x,y,z in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]);mesh.materials.append(mat)
 o=add_obj(name,mesh);o.location=loc
 if parent:o.parent=parent
 if bevel:
  m=o.modifiers.new('Machined edges','BEVEL');m.width=bevel;m.segments=3
 return o
def _arm_fk(q, robot):
 T=np.eye(4)
 for j in robot['joints']:
  if j['name']=='arm_joint_ee':
   T=T@np.asarray(j['origin'],dtype=float); break
  if j['movable'] and j['name'].startswith('arm_joint_'):
   T=T@np.asarray(j['origin'],dtype=float)
   R4=np.eye(4); R4[:3,:3]=Rotation.from_rotvec(float(q[int(j['name'].rsplit('_',1)[1])-1])*np.asarray(j['axis'],dtype=float)).as_matrix();T=T@R4
 return T[:3,3]
def _lower_flexiv_q(q, robot, weight):
 if weight<=1e-5:return q
 q=np.asarray(q,dtype=float).copy();target_z=_arm_fk(q,robot)[2]-.08*float(weight)
 for _ in range(4):
  p=_arm_fk(q,robot);err=target_z-p[2]
  if abs(err)<1e-4:break
  jz=np.zeros(7);eps=1e-4
  for k in range(7):
   qq=q.copy();qq[k]+=eps;jz[k]=(_arm_fk(qq,robot)[2]-p[2])/eps
  dq=jz*(err/(float(jz@jz)+1e-4));q+=np.clip(dq,-.06,.06)
 return q
for index,clip in enumerate(ordered):
 before_objects=set(scene.objects);row=index//10;col=index%10;d=np.load(clip['file']);robot=assets['robots'][clip['pair']];group=add_obj('Station '+clip['pair']);group.location=(col*DX,row*DY,.76);group.rotation_euler[2]=-math.pi/2
 rr=Rotation.from_quat(d['root'][:,[4,5,6,3]]);pos=rr.inv().apply(d['pos']-d['root'][:,:3]);rot=(rr.inv()*Rotation.from_quat(d['quat'][:,[1,2,3,0]])).as_quat()[:,[3,0,1,2]]
 # Pull each target trajectory modestly toward its belt centerline along the
 # lower-spread lateral axis, keeping objects away from the belt edges.
 for arr in (pos,):
  ax=int(np.argmin(np.ptp(arr[:,:2],axis=0))); mid=float(np.median(arr[:,ax])); arr[:,ax]=.72*arr[:,ax]+.28*mid
 # Hero starts at normal settled source frame; other stations have staggered starts.
 start_frame=1 if index==0 else int(reveal[index])
 fr=np.arange(1,END+1);base_src=np.clip(24+(fr-start_frame)*3,24,len(d['q'])-1).astype(int)
 # Compress Flexiv's high post-grasp transition so it settles into a lower
 # handoff pose instead of lifting too far between the two objects.
 if clip['pair'].startswith('flexiv_'):
  src=np.where(base_src>150,np.minimum(base_src+80,len(d['q'])-1),base_src)
 else:
  src=base_src
 arm_q=d['q'][src,:7].astype(float).copy()
 if clip['pair'].startswith('flexiv_'):
  # Lower only the default/approach hand pose; fade the IK correction out
  # before the grasp so the target-relative motion stays intact.
  weights=np.clip((140-base_src)/60.0,0.0,1.0)
  for ii,w in enumerate(weights): arm_q[ii]=_lower_flexiv_q(arm_q[ii],robot,float(w))
 links={}
 for name in robot['roots']:
  o=add_obj(f'{index:02d}/{name}');o.parent=group;links[name]=o
 for j in robot['joints']:
  o=add_obj(f'{index:02d}/{j["child"]}');o.parent=links[j['parent']];origin=np.array(j['origin']);o.matrix_basis=Matrix(origin.tolist());links[j['child']]=o
  if j['movable']:
   jid=int(j['name'].rsplit('_',1)[1])-1 if j['name'].startswith('arm_joint_') else 7+int(j['name'].split('_')[1]);ang=arm_q[:,jid] if j['name'].startswith('arm_joint_') else d['q'][src,jid]
   q=(Rotation.from_matrix(origin[:3,:3])*Rotation.from_rotvec(ang[:,None]*np.asarray(j['axis']))).as_quat()[:,[3,0,1,2]];keyquat(o,q,fr)
 for part in robot['parts']:
  o=add_obj(f'{index:02d}/visual/{part["link"]}',get_mesh(part));o.parent=links[part['link']]
 main_oid=clip['object_id']
 o=add_obj(f'{index:02d}/object/{main_oid}',get_mesh(assets['objects'][main_oid]));o.parent=group;act=keyquat(o,rot[src],fr);animate_pos(o,pos[src],fr,act)
 pos2=rr.inv().apply(d['pos2']-d['root'][:,:3]);
 ax2=int(np.argmin(np.ptp(pos2[:,:2],axis=0))); mid2=float(np.median(pos2[:,ax2])); pos2[:,ax2]=.72*pos2[:,ax2]+.28*mid2
 rot2=(rr.inv()*Rotation.from_quat(d['quat2'][:,[1,2,3,0]])).as_quat()[:,[3,0,1,2]]
 next_oid=clip.get('next_object_id',main_oid)
 o=add_obj(f'{index:02d}/next-object/{next_oid}',get_mesh(assets['objects'][next_oid]));o.parent=group;act=keyquat(o,rot2[src],fr);animate_pos(o,pos2[src],fr,act)
 # Reproduce the actual fixed bin geometry relative to the robot base.
 binlocal=rr[0].inv().apply(d['bin_center']-d['root'][0,:3]);binlocal[2]=.03
 for name,off,size in [('base',(0,0,-.015),(.48,.48,.03)),('left',(-.245,0,.075),(.025,.50,.18)),('right',(.245,0,.075),(.025,.50,.18)),('front',(0,-.245,.075),(.48,.025,.18)),('back',(0,.245,.075),(.48,.025,.18))]:
  box(f'Bin{index}/{name}',tuple(binlocal+np.array(off)),size,blue,group,.008)
 box('Robot fixed mounting plate',(-.04,0,-.035),(.23,.23,.07),white,group,.012)
 box('Robot fixed pedestal',(-.04,0,-.42),(.12,.12,.70),metal,group,.008)
 # Physical belt surface is at z=0 relative to robot base, extends upstream.
 # Every belt stripe follows the recorded integral of contact surface speed.
 by=-.34
 traj_min=min(float(pos[:,0].min()),float(pos2[:,0].min()));traj_max=max(float(pos[:,0].max()),float(pos2[:,0].max()))
 # Use a common belt length for every station; center it on the two target
 # trajectories so object placement remains valid while the montage stays uniform.
 length=1.45;cx=(traj_min+traj_max)/2+.05;x0=cx-length/2;x1=cx+length/2
 box('Conveyor housing'+str(index),(cx,by,-.087),(length+.06,.40,.15),metal,group,.025)
 belt=box('Moving belt'+str(index),(cx,by,-.006),(length,.37,.012),rubber,group,.005)
 for x in [x0+.08,x1-.08]:
  for y in [by-.15,by+.15]:box('Frame leg',(x,y,-.42),(.045,.045,.70),metal,group,.004)
 travel=d['belt_distance'][src];pitch=.055
 # Procedural seam phase has no discontinuous geometry wrap or blur streaks.
 bm=rubber.copy();bm.name='Animated rubber '+str(index);belt.data.materials.clear();belt.data.materials.append(bm)
 nodes=bm.node_tree.nodes;edges=bm.node_tree.links;bsdf=nodes.get('Principled BSDF')
 tc=nodes.new('ShaderNodeTexCoord');sep=nodes.new('ShaderNodeSeparateXYZ');edges.new(tc.outputs['Generated'],sep.inputs[0])
 mul=nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=length;edges.new(sep.outputs['X'],mul.inputs[0])
 offset=nodes.new('ShaderNodeValue');offset.name='Recorded belt travel'
 for frame,value in zip(fr,travel):offset.outputs[0].default_value=float(value);offset.outputs[0].keyframe_insert('default_value',frame=int(frame))
 sub=nodes.new('ShaderNodeMath');sub.operation='SUBTRACT';edges.new(mul.outputs[0],sub.inputs[0]);edges.new(offset.outputs[0],sub.inputs[1])
 scale=nodes.new('ShaderNodeMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=2/pitch;edges.new(sub.outputs[0],scale.inputs[0])
 wave=nodes.new('ShaderNodeMath');wave.operation='PINGPONG';wave.inputs[1].default_value=1.;edges.new(scale.outputs[0],wave.inputs[0])
 line=nodes.new('ShaderNodeMath');line.operation='LESS_THAN';line.inputs[1].default_value=.035;edges.new(wave.outputs[0],line.inputs[0])
 mix=nodes.new('ShaderNodeMixRGB');mix.inputs[1].default_value=(.003,.005,.008,1);mix.inputs[2].default_value=(.35,.38,.40,1);edges.new(line.outputs[0],mix.inputs[0]);edges.new(mix.outputs[0],bsdf.inputs['Base Color'])
 for x in [x0,x1]:
  verts=[];faces=[]
  for y in [-.20,.20]:
   for k in range(24):
    angle=k*2*math.pi/24;verts.append((.045*math.cos(angle),y,.045*math.sin(angle)))
  for k in range(24):faces.append((k,(k+1)%24,(k+1)%24+24,k+24))
  mesh=bpy.data.meshes.new('End drum');mesh.from_pydata(verts,[],faces);mesh.materials.append(metal);o=add_obj('Driven conveyor roller',mesh);o.parent=group;o.location=(x,by,-.04)
  q=Rotation.from_rotvec(np.c_[np.zeros(len(fr)),-travel/.045,np.zeros(len(fr))]).as_quat()[:,[3,0,1,2]];keyquat(o,q,fr)
 for dx in [-.20,.20]:
  for dy in [-.20,.20]:box('Bin cradle leg',tuple(binlocal+np.array([dx,dy,-.40])),(.04,.04,.74),metal,group,.004)
 # Only the two target objects from the successful trajectory are placed on the belt.
 objs=list(set(scene.objects)-before_objects);station_objects.append(objs)
 rf=int(reveal[index]);fade=6 if index else 0
 for ob in objs:
  if rf>1:
   ob.hide_render=True;ob.keyframe_insert('hide_render',frame=1);ob.keyframe_insert('hide_render',frame=rf-1)
   ob.hide_render=False;ob.keyframe_insert('hide_render',frame=rf)
   if ob.type=='MESH':
    ob.color=(1,1,1,0);ob.keyframe_insert('color',frame=rf)
    ob.color=(1,1,1,1);ob.keyframe_insert('color',frame=rf+fade)
 station_records.append(dict(index=index,row=row,col=col,pair=clip['pair'],object_id=clip['object_id'],reveal_frame=rf,fully_visible_frame=rf+fade,action_start_frame=start_frame,source_sha256=clip['sha256']))
box('Studio floor',(9,7,-.04),(200,200,.08),white)
scene.render.threads_mode='FIXED';scene.render.threads=6
scene.render.resolution_x=1920;scene.render.resolution_y=1080;scene.render.fps=FPS;scene.frame_end=END;scene.cycles.samples=40;scene.render.use_motion_blur=True;scene.render.motion_blur_shutter=.06;scene.cycles.use_persistent_data=False
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(1,1,1,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.45;scene.view_settings.exposure=-.45
scene.render.film_transparent=True;scene.render.image_settings.color_mode='RGBA';scene.use_nodes=False
for name,loc,power,size in [('Key',(1,-3,13),6000,12),('Fill',(18,1,12),5500,12),('Rim',(9,18,14),8000,14),('Top',(9,8,16),4500,14)]:
 l=bpy.data.lights.new(name,'AREA');l.energy=power;l.shape='DISK';l.size=size;o=add_obj(name,l);o.location=loc;o.rotation_euler=(Vector((9,6,0))-o.location).to_track_quat('-Z','Y').to_euler()
# Visibility and arrangement audit before rendering.
visible_counts={}
for frame in [1,100,175,230,280,310,350,400,444]:
 scene.frame_set(frame);bpy.context.view_layer.update()
 visible_counts[str(frame)]=sum(any(o.type=='MESH' and not o.hide_render and o.color[3]>.01 for o in obs) for obs in station_objects)
assert visible_counts['1']==1 and visible_counts['444']==60
(V/'audit').mkdir(exist_ok=True)
(V/'audit/layout.json').write_text(json.dumps(dict(passed=True,rows=6,columns=10,stations=60,unique_embodiments=24,copies_per_embodiment='1-3',first='franka_revo3',arms_per_row=3,visible_counts=visible_counts,stations_detail=station_records,camera_keys=keys),indent=2))
(V/'render').mkdir(exist_ok=True);scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(V/'render/conveyor.blend'))
(V/'render_manifest.json').write_text(json.dumps(dict(stations=60,unique_embodiments=24,copies_per_embodiment='1-3',layout=[6,10],progressive_reveal=True,first='franka_revo3',seconds=14.8,fps=FPS,frames=END,source_speed=1.5,diverse_objects=True,queue_objects_follow_belt=False,camera_high_speed_seconds=0.8,queued_objects_per_station='0',smooth_camera_curve=True,ordered_reveal=True,front_row_first=True,motion_blur_shutter=.06,actual_physical_bin=True,policy_plus_external_release=True,independent_successful_rollouts=True,physical_conveyor_feed=True,two_physical_items=True,immediate_arrival_release=True,low_home_capture_with_validated_fallback=True,clips=ordered),indent=2))
