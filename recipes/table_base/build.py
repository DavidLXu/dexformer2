from dexvideo.paths import stage
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
from native_helpers import *
from kinematics import fk
from scipy.interpolate import PchipInterpolator
V=(stage('table_base') / '')
SOURCE=(stage('capture_reference') / '')
END=450;fr=np.arange(1,END+1)
def box(name,loc,size,mat,bevel=.012,parent=None):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
 if parent:o.parent=parent
 if bevel:m=o.modifiers.new('Soft edges','BEVEL');m.width=bevel;m.segments=3
 return o
white=get_material(dict(type='principled',base_color={'type':'rgb','value':[.82,.85,.86]},roughness=.55))
tablemat=get_material(dict(type='principled',base_color={'type':'rgb','value':[.67,.74,.76]},roughness=.48))
metal=get_material(dict(type='principled',base_color={'type':'rgb','value':[.38,.45,.49]},metallic=.6,roughness=.35))
by={c['pair']:c for c in json.loads((V/'selection.json').read_text())['clips']}
arms=['franka','kuka','flexiv','xarm'];hands=['revo3','leap','sharpa','allegro','rapid','shadow']
pairs=[arms[i%4]+'_'+hands[(i//4+i%4)%6] for i in range(24)]
assert len(set(pairs))==24
# 12 robots on each side, alternating every .82m along one continuous table.
spacing=.82;last=23*spacing;table_min=-.62;table_max=last+.66;width=.60
box('Continuous central table',(0,(table_min+table_max)/2,.715),(width,table_max-table_min,.09),tablemat)
for y in np.arange(0,table_max,2.6):
 for x in [-.27,.27]:box('Table leg',(x,y,.34),(.045,.07,.68),metal)
floor=box('White floor',(0,10,-.055),(200,200,.1),white);floor.is_shadow_catcher=True
# Arrival schedule: linger on first grasps, then increase travel speed gradually.
arrivals=PchipInterpolator([0,1,3,7,15,23],[1.25,2.25,3.65,5.7,8.65,11.45])(np.arange(24))
records=[]
for i,pair in enumerate(pairs):
 c=by[pair];d=np.load(c['file']);assert hashlib.sha256(Path(c['file']).read_bytes()).hexdigest()==c['sha256']
 assert c['row']['success'] and not c['row']['abnormal']
 robot=assets['robots'][pair];rr=Rotation.from_quat(d['root'][:,[4,5,6,3]])
 pos=rr.inv().apply(d['pos']-d['root'][:,:3]);rot=(rr.inv()*Rotation.from_quat(d['quat'][:,[1,2,3,0]])).as_quat()[:,[3,0,1,2]]
 palm=fk(d['q'],robot)['palm_lower'][:,:3,3]
 candidates=np.flatnonzero((np.arange(len(pos))>=20)&(np.arange(len(pos))<100)&(palm[:,2]<.33)&(pos[:,2]<.10))
 assert len(candidates),pair
 start=int(candidates[0]);stop=179
 # Hold initial low approach until scheduled start, then play recorded grasp at 1x.
 begin=arrivals[i]-(.95 if i<4 else 1.35)
 src=np.clip(start+(fr/30-begin)*60,start,stop).astype(int)
 anchor=pos[start,:2];side=-1 if i%2==0 else 1
 yaw=(0 if side<0 else math.pi)-math.atan2(anchor[1],anchor[0])
 R=Rotation.from_euler('z',yaw);base=np.array([0,i*spacing,.76])-R.apply([*anchor,0])
 assert abs(base[0])>width/2+.12,(pair,base)
 group=add_obj('Station '+pair);group.location=base;group.rotation_euler[2]=yaw
 links={}
 for name in robot['roots']:o=add_obj(f'{i}/{name}');o.parent=group;links[name]=o
 for j in robot['joints']:
  o=add_obj(f'{i}/{j["child"]}');o.parent=links[j['parent']];origin=np.array(j['origin']);o.matrix_basis=Matrix(origin.tolist());links[j['child']]=o
  if j['movable']:
   jid=int(j['name'].rsplit('_',1)[1])-1 if j['name'].startswith('arm_joint_') else 7+int(j['name'].split('_')[1])
   q=(Rotation.from_matrix(origin[:3,:3])*Rotation.from_rotvec(d['q'][src,jid,None]*np.asarray(j['axis']))).as_quat()[:,[3,0,1,2]];keyquat(o,q,fr)
 for part in robot['parts']:o=add_obj(f'{i}/CAD/{part["link"]}',get_mesh(part));o.parent=links[part['link']]
 part=assets['objects'][c['object_id']];o=add_obj(f'{i}/Object',get_mesh(part));o.parent=group;act=keyquat(o,rot[src],fr);animate_pos(o,pos[src],fr,act)
 box('Separate robot mount',(base[0],base[1],.71),(.24,.30,.10),white)
 box('Separate robot pedestal',(base[0],base[1],.34),(.16,.20,.68),metal)
 verts=np.load(B/part['mesh'])['vertices'];margins=[]
 for s in range(start,180):
  if pos[s,2]>pos[start,2]+.025:continue
  vv=R.apply(Rotation.from_quat(rot[s,[1,2,3,0]]).apply(verts)+pos[s])+base
  margins.append(float(width/2-np.abs(vv[:,0]).max()))
 assert min(margins)>.09,(pair,min(margins))
 records.append(dict(pair=pair,object_id=c['object_id'],source_sha256=c['sha256'],source_file=c['file'],source_start=start,source_end=stop,arrival_seconds=float(arrivals[i]),begin_seconds=float(begin),initial_palm_height=float(palm[start,2]),table_edge_clearance=min(margins),base=base.tolist(),yaw=float(yaw),side=int(side)))
 print('STATION',pair,flush=True)
cam=add_obj('Camera',bpy.data.cameras.new('Camera'));scene.camera=cam;cam.data.lens=45;cam.data.clip_end=250
# A level, low dolly through the centre, with very small smooth lateral drift.
times=np.r_[0,arrivals,12.8,13.3,15.]
ys=np.r_[-1.9,np.arange(24)*spacing-1.0,last+1.2,last+3.2,last+5.2]
path=PchipInterpolator(times,ys);poses=[];qs=[]
for f in fr:
 t=(f-1)/30;y=float(path(t));exitmix=float(np.clip((t-11.8)/1.4,0,1));exitmix=exitmix*exitmix*(3-2*exitmix)
 eye=Vector((.055*math.sin(t*.9)*(1-exitmix),y,.99));target=Vector((0,y+1.65,.93+.06*exitmix))
 poses.append(eye[:]);qs.append((target-eye).to_track_quat('-Z','Y')[:])
act=keyquat(cam,qs,fr);animate_pos(cam,np.array(poses),fr,act)
clearance=[]
for rec in records:
 d=np.load(rec['source_file']);robot=assets['robots'][rec['pair']];src=np.clip(rec['source_start']+(fr/30-rec['begin_seconds'])*60,rec['source_start'],179).astype(int)
 ts=fk(d['q'][src],robot);camera_local=Rotation.from_euler('z',rec['yaw']).inv().apply(np.array(poses)-np.array(rec['base']))
 nearest=100.;nearest_frame=0
 for part in robot['parts']:
  verts=np.load(B/part['mesh'])['vertices'];lo=verts.min(0);hi=verts.max(0);T=ts[part['link']]
  local=np.einsum('nji,nj->ni',T[:,:3,:3],camera_local-T[:,:3,3]);delta=np.maximum(np.maximum(lo-local,local-hi),0);dist=np.linalg.norm(delta,axis=1);j=int(np.argmin(dist))
  if dist[j]<nearest:nearest=float(dist[j]);nearest_frame=j+1
 clearance.append(dict(pair=rec['pair'],conservative_camera_mesh_box_clearance=nearest,frame=nearest_frame))
assert min(r['conservative_camera_mesh_box_clearance'] for r in clearance)>.055,clearance
for k,y in enumerate(np.arange(-1,last+3,4)):
 light=bpy.data.lights.new(f'Softbox{k}','AREA');light.energy=650;light.shape='DISK';light.size=4
 o=add_obj(light.name,light);o.location=(-1.5 if k%2 else 1.5,y,5);o.rotation_euler=(Vector((0,y,.8))-o.location).to_track_quat('-Z','Y').to_euler()
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(1,1,1,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
scene.view_settings.exposure=-.45;scene.render.resolution_x=1920;scene.render.resolution_y=1080;scene.frame_end=END
scene.cycles.samples=24;scene.render.motion_blur_shutter=.16;scene.render.film_transparent=True;scene.render.image_settings.color_mode='RGBA'
(V/'render').mkdir(exist_ok=True);(V/'audit').mkdir(exist_ok=True)
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(V/'render/table.blend'))
(V/'audit/layout.json').write_text(json.dumps(dict(passed=True,stations=24,left=12,right=12,frames=450,fps=30,lens_mm=45,camera_height_above_table_m=.23,camera_clearance=clearance,source_playback_speed=1,unchanged_joint_and_object_tracks=True,selected_independent_rollouts=True,table_width=width,table_end=table_max,records=records),indent=2))
