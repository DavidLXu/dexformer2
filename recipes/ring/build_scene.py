from dexvideo.paths import stage
"""Native geometry + unmodified successful policy trajectories, rigidly staged."""
from pathlib import Path
import json,math,hashlib,time,sys
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from pacing import pacing,sample
import bpy
from mathutils import Matrix,Quaternion,Vector
ROOT=(stage('parade') / '');B=ROOT/'bundle'
FPS=30;END=450
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

def box(name,loc,size,mat,parent=None,bevel=0):
 verts=[(x*size[0]/2,y*size[1]/2,z*size[2]/2) for x,y,z in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]);mesh.materials.append(mat)
 o=add_obj(name,mesh);o.location=loc
 if parent:o.parent=parent
 if bevel:
  m=o.modifiers.new('Machined edges','BEVEL');m.width=bevel;m.segments=3
 return o

V=(stage('ring') / '')
M=json.loads((V/'selection.json').read_text());ordered=M['clips'];N=len(ordered)
assert 8<=N<=12 and ordered[0]['pair']=='franka_revo3'
metal=get_material(dict(type='principled',base_color={'type':'rgb','value':[.55,.6,.64]},metallic=.65,roughness=.3))
rubber=get_material(dict(type='principled',base_color={'type':'rgb','value':[.025,.035,.042]},roughness=.75))
blue=get_material(dict(type='principled',base_color={'type':'rgb','value':[.035,.32,.43]},roughness=.4))
white=get_material(dict(type='principled',base_color={'type':'rgb','value':[.82,.85,.86]},roughness=.55))
RADIUS=3.2
fr=np.arange(1,END+1)
# Low approach frames are selected from actual recorded motions: no root or joint edits.
def ee_positions(robot,qs):
 out=[]
 for q in qs:
  ts={k:np.eye(4) for k in robot['roots']}
  for j in robot['joints']:
   t=np.array(j['origin'],float)
   if j['movable'] and j['name'].startswith('arm_joint_'):
    r=np.eye(4);r[:3,:3]=Rotation.from_rotvec(q[int(j['name'].rsplit('_',1)[1])-1]*np.array(j['axis'])).as_matrix();t=t@r
   ts[j['child']]=ts[j['parent']]@t
   if j['name']=='arm_joint_ee':out.append(ts[j['child']][:3,3]);break
 return np.array(out)
clocks=[pacing(np.load(c['file'])) for c in ordered]
camera_departure=int(math.ceil(1+clocks[0]['elapsed'][ordered[0]['row']['release_steps'][1]+18-35]*FPS))+3
assert camera_departure<180,camera_departure
centers=[camera_departure+64,camera_departure+120,camera_departure+168]
reveal=[1,centers[0]-28,centers[1]-28,centers[2]-28]+np.rint(np.linspace(max(centers[2]+8,305),378,N-4)).astype(int).tolist()
records=[];all_station_objects=[]
for index,clip in enumerate(ordered):
 before=set(scene.objects)
 assert hashlib.sha256(Path(clip['file']).read_bytes()).hexdigest()==clip['sha256']
 assert clip['row']['success'] and not clip['row']['abnormal']
 d=np.load(clip['file']);robot=assets['robots'][clip['pair']]
 theta=-math.pi/2+index*2*math.pi/N
 # +y points towards the circle centre; local x is tangent.
 yaw=theta+math.pi/2;tangent=np.array([math.cos(yaw),math.sin(yaw)])
 center=RADIUS*np.array([math.cos(theta),math.sin(theta)])
 group=add_obj('Station '+clip['pair']);group.location=(*(center-.44*tangent),.76);group.rotation_euler[2]=yaw
 rr=Rotation.from_quat(d['root'][:,[4,5,6,3]])
 pos=np.stack([rr.inv().apply(d['pos'][:,j]-d['root'][:,:3]) for j in range(4)],axis=1)
 rot=np.stack([(rr.inv()*Rotation.from_quat(d['quat'][:,j][:,[1,2,3,0]])).as_quat()[:,[3,0,1,2]] for j in range(4)],axis=1)
 ee=ee_positions(robot,d['q'])
 start=35;rf=reveal[index]
 animation_start=1 if index==0 else rf+14
 clock=clocks[index]
 src=sample(clock,np.maximum(0,fr-animation_start)/FPS)
 left=np.floor(src).astype(int);right=np.minimum(left+1,len(d['q'])-1);fraction=src-left
 qsample=d['q'][left]*(1-fraction[:,None])+d['q'][right]*fraction[:,None]
 (V/'audit'/f'time_map_{index:02d}.json').write_text(json.dumps(dict(pair=clip['pair'],source_frames=src.tolist(),playback_rate=clock['rate'].tolist(),source_elapsed_video_seconds=clock['elapsed'].tolist()),indent=2))
 links={}
 for name in robot['roots']:
  o=add_obj(f'{index:02d}/{name}');o.parent=group;links[name]=o
 for j in robot['joints']:
  o=add_obj(f'{index:02d}/{j["child"]}');o.parent=links[j['parent']];origin=np.array(j['origin']);o.matrix_basis=Matrix(origin.tolist());links[j['child']]=o
  if j['movable']:
   jid=int(j['name'].rsplit('_',1)[1])-1 if j['name'].startswith('arm_joint_') else 7+int(j['name'].split('_')[1]);ang=qsample[:,jid]
   q=(Rotation.from_matrix(origin[:3,:3])*Rotation.from_rotvec(ang[:,None]*np.asarray(j['axis']))).as_quat()[:,[3,0,1,2]];keyquat(o,q,fr)
 for part in robot['parts']:
  o=add_obj(f'{index:02d}/visual/{part["link"]}',get_mesh(part));o.parent=links[part['link']]
 for j,oid in enumerate(clip['object_ids']):
  part=assets['objects'][oid]
  o=add_obj(f'{index:02d}/target{j}/{oid}',get_mesh(part));o.parent=group;qinterp=Slerp(np.arange(len(rot)),Rotation.from_quat(rot[:,j][:,[1,2,3,0]]))(src).as_quat()[:,[3,0,1,2]];act=keyquat(o,qinterp,fr);animate_pos(o,pos[left,j]*(1-fraction[:,None])+pos[right,j]*fraction[:,None],fr,act)
 binlocal=rr[0].inv().apply(d['bin_center']-d['root'][0,:3]);binlocal[2]=.03
 for name,off,size in [('base',(0,0,-.015),(.48,.48,.03)),('left',(-.245,0,.075),(.025,.50,.18)),('right',(.245,0,.075),(.025,.50,.18)),('front',(0,-.245,.075),(.48,.025,.18)),('back',(0,.245,.075),(.48,.025,.18))]:
  box(f'Bin{index}/{name}',tuple(binlocal+np.array(off)),size,blue,group,.008)
 for dx in [-.20,.20]:
  for dy in [-.20,.20]:box('Bin leg',tuple(binlocal+np.array([dx,dy,-.40])),(.04,.04,.74),metal,group,.004)
 box('Robot mount',(-.04,0,-.035),(.23,.23,.07),white,group,.012)
 box('Robot pedestal',(-.04,0,-.42),(.12,.12,.70),metal,group,.008)
 # Identical tangent pickup decks. Bounds are fixed for all units.
 cx,cy,length,width=.53,-.22,.80,.73
 box('Pickup deck housing',(cx,cy,-.067),(length+.04,width+.02,.11),metal,group,.018)
 box('Pickup deck',(cx,cy,-.006),(length,width,.012),rubber,group,.006)
 for x in [cx-length/2+.05,cx+length/2-.05]:
  for y in [cy-width/2+.05,cy+width/2-.05]:box('Deck leg',(x,y,-.42),(.04,.04,.70),metal,group,.004)
 for k in range(15):box('Deck seam',(cx-length/2+.04+k*.05,cy,.001),(.002,width-.02,.002),metal,group)
 # The source selector checks each of the four queued/grasped objects against this deck.
 assert clip['min_edge_margin_m']>.035
 obs=list(set(scene.objects)-before);all_station_objects.append(obs)
 if index:
  for ob in obs:
   ob.hide_render=True;ob.keyframe_insert('hide_render',frame=1);ob.keyframe_insert('hide_render',frame=rf-1)
   ob.hide_render=False;ob.keyframe_insert('hide_render',frame=rf)
   if ob.type=='MESH':
    ob.color=(1,1,1,0);ob.keyframe_insert('color',frame=rf)
    ob.color=(1,1,1,1);ob.keyframe_insert('color',frame=rf+14)
 records.append(dict(pair=clip['pair'],object_ids=clip['object_ids'],source_sha256=clip['sha256'],start_source_frame=start,animation_start_frame=animation_start,initial_ee_height_above_deck=float(ee[start,2]),min_object_edge_clearance_m=clip['min_edge_margin_m'],reveal_frame=rf,fully_visible_frame=rf+14,base_position=list(group.location),yaw=yaw,playback_speed='smooth variable shared clock',median_grasp_rate=float(np.median(clock['rate'][d['state']==1])),median_transfer_rate=float(np.median(clock['rate'][d['state']==2])),complete_step=clip['complete_step'],arrival_steps=clip['row']['arrival_steps'],release_steps=clip['row']['release_steps']))
 print('STATION',records[-1],flush=True)
box('White cyclorama',(0,0,-.04),(200,200,.08),white)
cam=add_obj('Camera',bpy.data.cameras.new('Camera'));scene.camera=cam
# Smooth polar camera avoids angular discontinuities and retains a level horizon.
from scipy.interpolate import PchipInterpolator
knots=[1,camera_departure,camera_departure+32,*centers,centers[2]+24,centers[2]+46,410,450]
angles=np.deg2rad([-90,-90,-90+180/N,-90+360/N,-90+720/N,-90+1080/N,24,38,44,46])
radii=[6.05,6.05,6.08,6.15,6.25,6.45,7.0,8.1,9.0,9.3]
heights=[2.05,2.05,2.08,2.18,2.35,2.65,4.8,8.4,12.6,13.5]
look_r=[3.23,3.23,3.23,3.23,3.23,3.1,2.3,1.1,.1,0]
look_z=[.96,.96,.96,.96,.96,.94,.88,.82,.76,.76]
interp=[PchipInterpolator(knots,x) for x in [angles,radii,heights,look_r,look_z]]
qs=[];positions=[]
for f in fr:
 a,r,h,lr,lz=[float(fn(f)) for fn in interp];eye=Vector((r*math.cos(a),r*math.sin(a),h));targ=Vector((lr*math.cos(a),lr*math.sin(a),lz));positions.append(eye[:]);q=(targ-eye).to_track_quat('-Z','Y');qs.append(q[:])
(V/'audit/camera.json').write_text(json.dumps(dict(frames=fr.tolist(),positions=positions,quaternions=qs,look_heights=[float(interp[4](f)) for f in fr]),indent=2))
act=keyquat(cam,qs,fr);animate_pos(cam,np.array(positions),fr,act);cam.data.lens=43;cam.data.clip_end=300
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(1,1,1,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
scene.view_settings.exposure=-.35;scene.render.film_transparent=True;scene.render.image_settings.color_mode='RGBA'
scene.cycles.samples=32;scene.render.motion_blur_shutter=.30
for name,loc,power,size in [('Key',(-4,-6,10),2800,8),('Fill',(7,-1,8),1800,7),('Rim',(-2,7,10),3200,8)]:
 l=bpy.data.lights.new(name,'AREA');l.energy=power;l.shape='DISK';l.size=size;o=add_obj(name,l);o.location=loc;o.rotation_euler=(Vector((0,0,.5))-o.location).to_track_quat('-Z','Y').to_euler()
(V/'render').mkdir(exist_ok=True);scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(V/'render/ring.blend'))
(V/'audit/layout.json').write_text(json.dumps(dict(passed=True,stations=N,objects_per_station=4,arm_families=len({c["pair"].split("_")[0] for c in ordered}),hand_families=len({c["pair"].split("_")[1] for c in ordered}),frames=END,fps=30,seconds=15,source_playback_speed="variable shared clock; recorded spatial paths retained; no new physics run",camera_departure_frame=camera_departure,root_unchanged_in_local_coordinates=True,spatial_paths_preserved=True,time_reparameterized=True,physics_rerun=False,independent_successful_rollouts=True,external_release=True,external_ik_transfer=True,external_low_return=True,deck_dimensions=[length,width],stations_detail=records),indent=2))
