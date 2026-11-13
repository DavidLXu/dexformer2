from dexvideo.paths import stage
"""Camera-only revision: fixed opening, forward descent, straight centreline."""
from pathlib import Path
import sys,json,hashlib,math
import bpy,numpy as np
from scipy.interpolate import CubicHermiteSpline
from scipy.spatial.transform import Rotation
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from kinematics import fk
OLD=(stage('table_objects') / '')
R=(stage('table') / '')
B=(stage('parade') / 'bundle')
bpy.ops.wm.open_mainfile(filepath=str(OLD/'render/table.blend'))
s=bpy.context.scene;cam=s.camera;act=cam.animation_data.action
def other_hash():
 out=[]
 for o in sorted(s.objects,key=lambda o:o.name):
  if o==cam or not o.animation_data or not o.animation_data.action:continue
  out.append([o.name,[[fc.data_path,fc.array_index,[[*k.co,k.interpolation] for k in fc.keyframe_points]] for fc in o.animation_data.action.fcurves]])
 return hashlib.sha256(json.dumps(out).encode()).hexdigest()
before=other_hash();original_pos=[];original_forward=[]
for f in range(1,451):
 s.frame_set(f);original_pos.append(list(cam.location));original_forward.append(list(cam.rotation_quaternion@Vector((0,0,-1))))
original_pos=np.array(original_pos);original_forward=np.array(original_forward)
join=3.3;join_index=99;end_y=original_pos[join_index,1];end_z=original_pos[join_index,2]
end_vy=(original_pos[join_index+1,1]-original_pos[join_index-1,1])*15
end_pitch=math.atan2(original_forward[join_index,2],np.linalg.norm(original_forward[join_index,:2]))
start_y=-2.30;start_z=1.22;start_pitch=math.radians(-4.5)
ys=CubicHermiteSpline([2.6,join],[start_y,end_y],[0,end_vy])
zs=CubicHermiteSpline([2.6,join],[start_z,end_z],[0,0])
ps=CubicHermiteSpline([2.6,join],[start_pitch,end_pitch],[0,0])
positions=[];quats=[];forwards=[]
for i in range(450):
 t=i/30
 if t<=2.6:y,z,pitch=start_y,start_z,start_pitch
 elif t<join:y,z,pitch=float(ys(t)),float(zs(t)),float(ps(t))
 else:
  y,z=original_pos[i,1:];d=original_forward[i];pitch=math.atan2(d[2],np.linalg.norm(d[:2]))
 direction=Vector((0,math.cos(pitch),math.sin(pitch)))
 positions.append([0.,float(y),float(z)]);quats.append(list(direction.to_track_quat('-Z','Y')));forwards.append(list(direction))
for fc in act.fcurves:
 if fc.data_path not in ['location','rotation_quaternion']:continue
 values=positions if fc.data_path=='location' else quats
 for i,k in enumerate(fc.keyframe_points):k.co.y=values[i][fc.array_index]
 fc.update()
cam.update_tag();s.frame_set(1);bpy.context.view_layer.update()
assert other_hash()==before
positions=np.array(positions);quats=np.array(quats);forwards=np.array(forwards)
assert np.max(np.abs(positions[:,0]))==0 and np.max(np.abs(forwards[:,0]))==0
assert np.max(np.abs(positions[:79]-positions[0]))==0 and np.max(np.abs(quats[:79]-quats[0]))==0
assert np.min(np.diff(positions[:,1]))>=-1e-6
assert np.all(np.diff(positions[78:100,1])>0) and np.all(np.diff(positions[78:100,2])<0)
layout=json.loads((stage('table_base') / 'audit/layout.json').read_text());assets=json.loads((B/'assets.json').read_text());clearance=[]
times=np.arange(450)/30
for i,c in enumerate(layout['records']):
 d=np.load(c['source_file']);robot=assets['robots'][c['pair']];ot=times if i==0 else np.clip(1.3+(times-4.25)/.76,0,449/30)
 src=np.clip(c['source_start']+(ot+1/30-c['begin_seconds'])*60,c['source_start'],179)
 qq=np.stack([np.interp(src,np.arange(len(d['q'])),d['q'][:,j]) for j in range(d['q'].shape[1])],axis=1)
 ts=fk(qq,robot);localcam=Rotation.from_euler('z',c['yaw']).inv().apply(positions-np.array(c['base']));nearest=100.
 for part in robot['parts']:
  verts=np.load(B/part['mesh'])['vertices'];lo=verts.min(0);hi=verts.max(0);T=ts[part['link']]
  local=np.einsum('nji,nj->ni',T[:,:3,:3],localcam-T[:,:3,3]);dist=np.linalg.norm(np.maximum(np.maximum(lo-local,local-hi),0),axis=1);nearest=min(nearest,float(dist.min()))
 clearance.append(dict(pair=c['pair'],conservative_camera_mesh_box_clearance=nearest))
assert min(c['conservative_camera_mesh_box_clearance'] for c in clearance)>.045,clearance
# Ensure the first actual target remains within the shot throughout its grasp.
from bpy_extras.object_utils import world_to_camera_view
target=bpy.data.objects['0/Object'];margins=[]
for f in range(1,46):
 s.frame_set(f);bpy.context.view_layer.update()
 for corner in target.bound_box:
  v=world_to_camera_view(s,cam,target.matrix_world@Vector(corner));margins.append(min(v.x,1-v.x,v.y,1-v.y));assert v.z>0
assert min(margins)>.015,min(margins)
(R/'audit').mkdir(exist_ok=True);(R/'render').mkdir(exist_ok=True);s.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'render/table.blend'))
(R/'audit/camera.json').write_text(json.dumps(dict(passed=True,only_camera_changed=True,other_animation_sha256=before,opening_fixed_through_s=2.6,opening_position=positions[0].tolist(),opening_pitch_deg=-4.5,descent_start_s=2.6,descent_end_s=3.3,descent_forward_distance_m=float(positions[99,1]-positions[78,1]),descent_vertical_distance_m=float(positions[78,2]-positions[99,2]),max_lateral_position_m=0,max_lateral_look_direction=0,opening_target_min_screen_margin=float(min(margins)),camera_clearance=clearance),indent=2))
print('CAMERA_READY',flush=True)
