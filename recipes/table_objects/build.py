from dexvideo.paths import stage
"""Higher opening, objects first, then waiting robots and recorded grasps."""
from pathlib import Path
import json,math,sys
import bpy,numpy as np
from scipy.interpolate import CubicHermiteSpline
from scipy.spatial.transform import Rotation
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from kinematics import fk
OLD=(stage('table_base') / '')
R=(stage('table_objects') / '')
B=(stage('parade') / 'bundle')
bpy.ops.wm.open_mainfile(filepath=str(OLD/'render/table.blend'))
scene=bpy.context.scene;layout=json.loads((OLD/'audit/layout.json').read_text());assets=json.loads((B/'assets.json').read_text())
fr=np.arange(1,451);times=(fr-1)/30
# Original nonhero time1.3 starts at new4.25. After the staged introduction,
# the existing sequence runs at1/.76 speed, retaining a15second total film.
def old_time(t):return np.clip(1.3+(np.asarray(t)-4.25)/.76,0,449/30)
def fade(objects,start_s,end_s):
 start=round(start_s*30)+1;end=round(end_s*30)+1
 for o in objects:
  o.hide_render=True;o.keyframe_insert('hide_render',frame=1);o.keyframe_insert('hide_render',frame=start-1)
  o.hide_render=False;o.keyframe_insert('hide_render',frame=start)
  o.color=(1,1,1,0);o.keyframe_insert('color',frame=1);o.keyframe_insert('color',frame=start)
  o.color=(1,1,1,1);o.keyframe_insert('color',frame=end)
  for fc in o.animation_data.action.fcurves:
   if fc.data_path=='color':
    for k in fc.keyframe_points:k.interpolation='BEZIER';k.handle_left_type='AUTO_CLAMPED';k.handle_right_type='AUTO_CLAMPED'
records=[];mapping_errors=[]
for i,c in enumerate(layout['records']):
 group=bpy.data.objects['Station '+c['pair']];members=list(group.children_recursive);target=bpy.data.objects[f'{i}/Object']
 robot_meshes=[o for o in members if o.type=='MESH' and o!=target]
 for prefix in ['Separate robot mount','Separate robot pedestal']:
  matches=[o for o in scene.objects if o.name.startswith(prefix) and abs(o.location.x-c['base'][0])<1e-5 and abs(o.location.y-c['base'][1])<1e-5];assert len(matches)==1;robot_meshes+=matches
 if i:
  # Resample the exact existing position/quaternion curves; no new pose or IK.
  oldframes=old_time(times)*30+1
  for o in members:
   if not o.animation_data or not o.animation_data.action:continue
   for fc in o.animation_data.action.fcurves:
    if fc.data_path not in ['location','rotation_quaternion','rotation_euler','scale']:continue
    values=np.array([fc.evaluate(float(f)) for f in oldframes])
    assert len(fc.keyframe_points)==450
    for j,k in enumerate(fc.keyframe_points):k.co.y=values[j]
    fc.update();mapping_errors.append(float(max(abs(fc.evaluate(float(f))-v) for f,v in zip(fr,values))))
  object_start=1.55+.012*(i-1);object_full=object_start+.70
  arm_start=3.35+.09*(i-1);arm_full=arm_start+.85
  fade([target],object_start,object_full);fade(robot_meshes,arm_start,arm_full)
  grasp_begin=4.25+(c['begin_seconds']-1.3)*.76
  assert object_full<2.6 and arm_start>=3.35 and grasp_begin>=arm_full-.001,(c['pair'],grasp_begin,arm_full)
 else:object_start=object_full=arm_start=arm_full=0.;grasp_begin=c['begin_seconds']
 records.append(dict(pair=c['pair'],object_start_s=object_start,object_full_s=object_full,arm_start_s=arm_start,arm_full_s=arm_full,grasp_begin_s=grasp_begin))
assert max(mapping_errors)<1e-5
camera=scene.camera;act=camera.animation_data.action
locfc={fc.array_index:fc for fc in act.fcurves if fc.data_path=='location'};rotfc={fc.array_index:fc for fc in act.fcurves if fc.data_path=='rotation_quaternion'}
join=3.3;joinold=float(old_time(join))*30+1;joinloc=np.array([locfc[k].evaluate(joinold) for k in range(3)]);joinrot=np.array([rotfc[k].evaluate(joinold) for k in range(4)])
eps=.005;vy=(locfc[1].evaluate(float(old_time(join+eps))*30+1)-locfc[1].evaluate(float(old_time(join-eps))*30+1))/(2*eps)
knots=[0,.78,1.45,2.60,join]
ys=CubicHermiteSpline(knots,[-2.15,-2.15,-2.10,-2.05,joinloc[1]],[0,0,.08,.15,vy])
zs=CubicHermiteSpline(knots,[1.22,1.22,1.22,1.22,.99],[0,0,0,0,0])
xs=CubicHermiteSpline([0,2.60,join],[0,0,joinloc[0]],[0,0,0])
pitch=CubicHermiteSpline(knots,np.deg2rad([-7.7,-7.7,1.5,-5.,math.degrees(math.atan2(-.06,1.65))]),[0,0,0,0,0])
poses=[];rotations=[]
for t in times:
 if t<join:
  eye=Vector((float(xs(t)),float(ys(t)),float(zs(t))));direction=Vector((-eye.x,1.65,1.65*math.tan(float(pitch(t)))));q=direction.to_track_quat('-Z','Y');poses.append(list(eye));rotations.append(list(q))
 else:
  of=float(old_time(t))*30+1;poses.append([locfc[k].evaluate(of) for k in range(3)]);rotations.append([rotfc[k].evaluate(of) for k in range(4)])
for fc in act.fcurves:
 if fc.data_path not in ['location','rotation_quaternion']:continue
 values=poses if fc.data_path=='location' else rotations
 for j,k in enumerate(fc.keyframe_points):k.co.y=values[j][fc.array_index]
 fc.update()
# Verify camera separation using interpolated source joints and conservative
# part boxes; per-frame visible geometry is also reviewed in rendered previews.
clearance=[];timing=[]
for i,c in enumerate(layout['records']):
 d=np.load(c['source_file']);robot=assets['robots'][c['pair']];ot=times if i==0 else old_time(times)
 src=np.clip(c['source_start']+((ot+1/30)-c['begin_seconds'])*60,c['source_start'],179)
 qq=np.stack([np.interp(src,np.arange(len(d['q'])),d['q'][:,j]) for j in range(d['q'].shape[1])],axis=1)
 ts=fk(qq,robot);localcam=Rotation.from_euler('z',c['yaw']).inv().apply(np.array(poses)-np.array(c['base']));nearest=100.
 for part in robot['parts']:
  verts=np.load(B/part['mesh'])['vertices'];lo=verts.min(0);hi=verts.max(0);T=ts[part['link']]
  local=np.einsum('nji,nj->ni',T[:,:3,:3],localcam-T[:,:3,3]);distance=np.linalg.norm(np.maximum(np.maximum(lo-local,local-hi),0),axis=1);nearest=min(nearest,float(distance.min()))
 clearance.append(dict(pair=c['pair'],conservative_camera_mesh_box_clearance=nearest))
 rawpos=Rotation.from_quat(d['root'][:,[4,5,6,3]]).inv().apply(d['pos']-d['root'][:,:3]);err=np.linalg.norm(rawpos[:180]-d['goal'][:180,:3],axis=1);streak=0;stable=None
 for j,ok in enumerate(err<.05):
  streak=streak+1 if ok else 0
  if streak>=20 and stable is None:stable=j
 assert stable is not None
 original_t=c['begin_seconds']+(stable-c['source_start'])/60;stable_t=original_t if i==0 else 4.25+(original_t-1.3)*.76
 timing.append(dict(pair=c['pair'],stable_grasp_time_s=stable_t))
assert min(c['conservative_camera_mesh_box_clearance'] for c in clearance)>.045,clearance
assert max(t['stable_grasp_time_s'] for t in timing)<12.3
scene.frame_set(1);assert not bpy.data.objects['0/Object'].hide_render
for i in range(1,24):assert bpy.data.objects[f'{i}/Object'].hide_render
scene.frame_set(79) # 2.6s: all queued objects visible, all future robots hidden.
for i in range(1,24):
 assert not bpy.data.objects[f'{i}/Object'].hide_render
 assert bpy.data.objects[f'{i}/Object'].color[3]>.999
 assert all(o.hide_render for o in bpy.data.objects['Station '+layout['records'][i]['pair']].children_recursive if o.type=='MESH' and o.name!=f'{i}/Object')
(R/'render').mkdir(exist_ok=True);(R/'audit').mkdir(exist_ok=True);(R/'frames').mkdir(exist_ok=True)
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(R/'render/table.blend'))
(R/'audit/staging.json').write_text(json.dumps(dict(passed=True,opening_camera_height_above_table_m=.46,later_camera_height_above_table_m=.23,lens_mm=45,camera_return_complete_s=3.3,original_poses_retimed_only=True,max_motion_resampling_error=max(mapping_errors),later_playback_speed=1/.76,records=records,camera_clearance=clearance,grasp_timing=timing),indent=2))
print('SCENE_READY',flush=True)
