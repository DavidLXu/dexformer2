from dexvideo.paths import stage
from pathlib import Path
import sys,argparse
sys.path.insert(0,str(Path(__file__).parent))
from native_helpers import *
V=(stage('apples') / '')
p=argparse.ArgumentParser();p.add_argument('--index',type=int,required=True);a=p.parse_args()
c=json.loads((V/'selection.json').read_text())['clips'][a.index];d=np.load(c['file']);robot=assets['robots'][c['pair']]
assert hashlib.sha256(Path(c['file']).read_bytes()).hexdigest()==c['sha256']
from kinematics import fk
r=Rotation.from_quat(d['root'][:,[4,5,6,3]]);pos=r.inv().apply(d['pos']-d['root'][:,:3]);T=fk(d['q'],robot);palm=T['palm_lower'][:,:3,3];rot=(r.inv()*Rotation.from_quat(d['quat'][:,[1,2,3,0]])).as_quat()[:,[3,0,1,2]]
start=c['source_start'];src=np.arange(start,c['source_end']+1);N=len(src);assert N==c['frames']
fr=np.arange(1,N+1);q=d['q'][src];anchor=np.array([pos[start,0],pos[start,1],0.]);group=add_obj('Recorded robot frame');group.location=-anchor
links={}
for n in robot['roots']:o=add_obj(n);o.parent=group;links[n]=o
for j in robot['joints']:
 o=add_obj(j['child']);o.parent=links[j['parent']];origin=np.array(j['origin']);o.matrix_basis=Matrix(origin.tolist());links[j['child']]=o
 if j['movable']:
  jid=int(j['name'].rsplit('_',1)[1])-1 if j['name'].startswith('arm_joint_') else 7+int(j['name'].split('_')[1])
  quat=(Rotation.from_matrix(origin[:3,:3])*Rotation.from_rotvec(q[:,jid,None]*np.asarray(j['axis']))).as_quat()[:,[3,0,1,2]];keyquat(o,quat,fr)
for part in robot['parts']:
 o=add_obj('CAD/'+part['link'],get_mesh(part));o.parent=links[part['link']]
o=add_obj('Recorded apple',get_mesh(assets['objects']['013_apple']));o.parent=group;action=keyquat(o,rot[src],fr);animate_pos(o,pos[src],fr,action)
# The same broad support surface is centered on the pickup, safely away from edges.
white=get_material(dict(type='principled',base_color={'type':'rgb','value':[.84,.87,.88]},roughness=.65))
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,-.035));table=bpy.context.object;table.name='Support surface';table.dimensions=(20,20,.07);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);table.data.materials.append(white)
cam=add_obj('Camera',bpy.data.cameras.new('Camera'));scene.camera=cam
# Consistent close-up across all hands, without altering their poses.
from scipy.ndimage import gaussian_filter1d
cam.data.type='ORTHO';cam.data.ortho_scale=.85
view_offset={'franka_sharpa':(1.45,1.75,.89),'franka_allegro':(2.1,.5,1.05),'kuka_leap':(1.45,1.75,.89)}.get(c['pair'],(1.45,-1.75,.89))
centers=gaussian_filter1d((palm[src]+pos[src])*.5-anchor,sigma=7,axis=0,mode='nearest');centers[:,2]+=.025
for frame,center in zip(fr,centers):
 target=Vector(center);cam.location=target+Vector(view_offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.keyframe_insert('location',frame=int(frame));cam.keyframe_insert('rotation_euler',frame=int(frame))
for fc in cam.animation_data.action.fcurves:
 for kp in fc.keyframe_points:kp.interpolation='LINEAR'
target=Vector((0,0,.3))
for name,loc,power,size in [('Key',(1,-2,4),550,4),('Fill',(-2,0,3),400,3),('Rim',(0,3,3),650,3)]:
 l=bpy.data.lights.new(name,'AREA');l.energy=power;l.shape='DISK';l.size=size;o=add_obj(name,l);o.location=loc;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(1,1,1,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
scene.view_settings.exposure=-.85;scene.render.resolution_x=1280;scene.render.resolution_y=960;scene.frame_end=N;scene.cycles.samples=20;scene.render.motion_blur_shutter=.12;scene.render.film_transparent=True;scene.render.image_settings.color_mode='RGBA'
# Independent numpy FK vs Blender reconstruction. This capture has no logged palm pose.
# Check actual hand mesh bounds and apple bounds over the entire clip, not just joint centers.
hand_bounds=[]
for part in robot['parts']:
 if part['link'].startswith('arm_'):continue
 vertices=np.load(B/part['mesh'])['vertices'];lo=vertices.min(axis=0);hi=vertices.max(axis=0)
 corners=np.array([[x,y,z,1] for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]]])
 hand_bounds.append((part['link'],corners))
objverts=np.load(B/assets['objects']['013_apple']['mesh'])['vertices'];lo=objverts.min(axis=0);hi=objverts.max(axis=0);oc=np.array([[x,y,z] for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]]])
errs=[];maxx=0.;maxy=0.
for i in range(N):
 scene.frame_set(i+1);bpy.context.view_layer.update();actual=np.array(links['palm_lower'].matrix_world.translation);expect=palm[src[i]]-anchor;errs.append(float(np.linalg.norm(actual-expect)))
 points=[(T[name][src[i]]@corners.T).T[:,:3]-anchor for name,corners in hand_bounds]
 points.append(Rotation.from_quat(rot[src[i],[1,2,3,0]]).apply(oc)+pos[src[i]]-anchor)
 points=np.concatenate(points);hom=np.c_[points,np.ones(len(points))];view=(np.array(cam.matrix_world.inverted())@hom.T).T
 maxx=max(maxx,float(np.max(np.abs(view[:,0]))));maxy=max(maxy,float(np.max(np.abs(view[:,1]))))
assert max(errs)<1e-4,(c['pair'],max(errs))
# Four percent screen padding around all hand/object AABBs. At least previous shot scale.
cam.data.ortho_scale=max(.85,maxx/.46,maxy/(.46*.75))
margin=min(.5-maxx/cam.data.ortho_scale,.5-maxy/(cam.data.ortho_scale*.75))
assert margin>=.039
(V/'render').mkdir(exist_ok=True);(V/'audit').mkdir(exist_ok=True)
(V/'audit'/f'{a.index}.json').write_text(json.dumps(dict(passed=True,pair=c['pair'],source_start=start,source_end=int(src[-1]),frames=N,seconds=N/30,source_fps=60,output_fps=30,playback_speed=.5,max_numpy_blender_fk_error_m=max(errs),min_hand_object_mesh_screen_margin=margin,orthographic_scale=cam.data.ortho_scale,root_unchanged=True,joint_and_object_trajectory_unchanged=True,source_sha256=c['sha256']),indent=2))
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(V/'render'/f'{a.index}.blend'))
