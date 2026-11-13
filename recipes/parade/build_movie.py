from dexvideo.paths import stage
"""Native geometry + unmodified successful policy trajectories, rigidly staged."""
from pathlib import Path
import json,math,hashlib,time,sys
import numpy as np
from scipy.spatial.transform import Rotation
import bpy
from mathutils import Matrix,Quaternion,Vector
ROOT=(stage('parade') / '');B=ROOT/'bundle'
assets=json.loads((B/'assets.json').read_text());manifest=json.loads((B/'clips.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='GPU';scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.cycles.use_persistent_data=False
scene.cycles.max_bounces=6;scene.cycles.diffuse_bounces=3;scene.cycles.glossy_bounces=3;scene.cycles.transparent_max_bounces=4
scene.render.resolution_x=1920;scene.render.resolution_y=1080;scene.render.resolution_percentage=100;scene.render.fps=30;scene.frame_start=1;scene.frame_end=420
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.film_transparent=False
scene.render.use_motion_blur=True;scene.render.motion_blur_shutter=.45
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

# All 24 morphologies, four object episodes each, in a regular 12 x 8 parade.
slots=[(5,0),(6,0),(5,1),(6,1)]+[(x,y) for y in range(8) for x in range(12) if (x,y) not in [(5,0),(6,0),(5,1),(6,1)]]
clips=manifest['clips'];ordered=clips[:4];rest=clips[4:]
# Interleave arm/hand types across each row while preserving every selected case.
rest=sorted(rest,key=lambda e:(e['row']['case_index']%4,e['object_id'],e['pair']))
ordered+=rest;audits=[];starts=[]
for index,(clip,(col,row)) in enumerate(zip(ordered,slots)):
 assert hashlib.sha256((B/clip['file']).read_bytes()).hexdigest()==clip['sha256']
 d=np.load(B/clip['file']);robot=assets['robots'][clip['pair']];group=add_obj(f'Unit {index:03d} {clip["pair"]}');group.location=((col-5.5)*1.7,row*1.8,0);group.rotation_euler[2]=-math.pi/2
 start=[1,72,80,90][index] if index<4 else 215+((index*37)%113)
 starts.append(start);source=np.arange(25,240,2);frames=start+(source-25)/2;source=np.r_[25,source,239,239];frames=np.r_[1,frames, start+107,420]
 # Keep frames increasing, discard duplicate first/last holds and crop beyond duration.
 keep=np.r_[True,np.diff(frames)>0];source=source[keep];frames=frames[keep]
 roots=d['robot_pose'];rootrot=Rotation.from_quat(roots[:,[4,5,6,3]]);objpos=rootrot.inv().apply(d['object_pos']-roots[:,:3]);objrot=(rootrot.inv()*Rotation.from_quat(d['object_quat'][:,[1,2,3,0]])).as_quat()[:,[3,0,1,2]]
 links={}
 for name in robot['roots']:
  e=add_obj(f'{index:03d}/{name}');e.parent=group;links[name]=e
 world={name:np.eye(4) for name in robot['roots']};error=[]
 for j in robot['joints']:
  e=add_obj(f'{index:03d}/{j["child"]}');e.parent=links[j['parent']];origin=np.array(j['origin']);e.matrix_basis=Matrix(origin.tolist());links[j['child']]=e
  if j['movable']:
   jid=int(j['name'].rsplit('_',1)[1])-1 if j['name'].startswith('arm_joint_') else 7+int(j['name'].split('_')[1]);ang=d['q'][source,jid]
   rot=(Rotation.from_matrix(origin[:3,:3])*Rotation.from_rotvec(ang[:,None]*np.asarray(j['axis']))).as_quat()[:,[3,0,1,2]];keyquat(e,rot,frames)
 for part in robot['parts']:
  e=add_obj(f'{index:03d}/visual/{part["link"]}',get_mesh(part));e.parent=links[part['link']]
 obj=add_obj(f'{index:03d}/object/{clip["object_id"]}',get_mesh(assets['objects'][clip['object_id']]));obj.parent=group;act=keyquat(obj,objrot[source],frames);animate_pos(obj,objpos[source],frames,act)
 # Independently audit FK against simulator body poses at sampled actual frames.
 for sf in [25,60,120,180,239]:
  w={n:np.eye(4) for n in robot['roots']}
  for j in robot['joints']:
   t=np.array(j['origin'])
   if j['movable']:
    jid=int(j['name'].rsplit('_',1)[1])-1 if j['name'].startswith('arm_joint_') else 7+int(j['name'].split('_')[1]);t[:3,:3]=t[:3,:3]@Rotation.from_rotvec(np.asarray(j['axis'])*d['q'][sf,jid]).as_matrix()
   w[j['child']]=w[j['parent']]@t
  for name,p in zip(clip['body_names'],d['body_pose'][sf]):error.append(np.linalg.norm(w[name][:3,3]-rootrot[sf].inv().apply(p[:3]-roots[sf,:3])))
 assert max(error)<.004,(clip['pair'],max(error))
 audits.append(dict(index=index,pair=clip['pair'],object_id=clip['object_id'],source=clip['source'],sha256=clip['sha256'],max_fk_error_m=max(error),start_movie_frame=int(start),source_frames=[25,239],source_fps=60,group_translation=list(group.location),group_yaw_degrees=-90))
 print('UNIT',index,clip['pair'],clip['object_id'],max(error),flush=True)

bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.004));floor=bpy.context.object;floor.name='Continuous white studio surface';floor.data.materials.append(get_material(dict(type='principled',base_color={'type':'rgb','value':[.93,.93,.93]},roughness=.7)))
# Broad soft boxes remain fixed in world space throughout the camera motion.
def area(name,position,energy,size,target):
 light=bpy.data.lights.new(name,'AREA');light.energy=energy;light.shape='DISK';light.size=size;o=add_obj(name,light);o.location=position;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
area('Key softbox',(-5,-5,12),6500,9,(0,5,0));area('Fill softbox',(10,-1,9),4200,8,(0,5,0));area('Rear softbox',(0,16,12),8500,10,(0,5,0))
sun=bpy.data.lights.new('Soft daylight','SUN');sun.energy=1.6;sun.angle=.3;o=add_obj('Soft daylight',sun);o.rotation_euler=(.4,-.5,-.3)
camdata=bpy.data.cameras.new('Camera');camera=add_obj('Camera',camdata);scene.camera=camera;camdata.lens=43;camdata.clip_end=300
# Smooth close observation, fast horizontal reveal, a low pass, then a big pullback.
keys=[
 (1,(-.10,-1.95,1.10),(-.85,-.48,.30),48),
 (76,(-.35,-2.25,1.20),(-.85,-.45,.36),48),
 (91,(1.10,-3.10,1.65),(0,-.30,.39),43),
 (148,(1.02,-3.35,1.75),(0,-.25,.38),43),
 (171,(1.8,-4.8,3.4),(0,.55,.35),43),
 (219,(1.5,-5.0,3.5),(0,.6,.35),43),
 (239,(-5.1,-2.2,1.7),(-4.2,2.2,.42),35),
 (281,(5.6,-1.6,2.1),(4.0,3.0,.45),35),
 (300,(6.3,-2.3,3.5),(2,5,.35),38),
 (363,(17,-23,23),(0,6.0,.25),43),
 (420,(18,-24,24),(0,6.1,.25),43)]
for frame,loc,target,lens in keys:
 camera.location=loc;camera.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler();camera.keyframe_insert('location',frame=frame);camera.keyframe_insert('rotation_euler',frame=frame);camdata.lens=lens;camdata.keyframe_insert('lens',frame=frame)
for datablock in [camera,camdata]:
 for f in datablock.animation_data.action.fcurves:
  for k in f.keyframe_points:k.interpolation='BEZIER';k.handle_left_type='AUTO_CLAMPED';k.handle_right_type='AUTO_CLAMPED'
scene.frame_set(1);scene.render.filepath=str(ROOT/'frames/frame_0001.png')
(ROOT/'render').mkdir(exist_ok=True);(ROOT/'frames').mkdir(exist_ok=True)
(ROOT/'render/trajectory_audit.json').write_text(json.dumps(dict(passed=True,robots=96,embodiments=24,objects=len(set(e['object_id'] for e in clips)),max_fk_error_m=max(e['max_fk_error_m'] for e in audits),entries=audits,purpose=manifest['purpose']),indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'render/parade.blend'))
print('BUILT',len(mesh_cache),'meshes',len(mat_cache),'materials',flush=True)
