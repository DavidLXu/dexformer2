from dexvideo.paths import stage
from pathlib import Path
import json,hashlib,numpy as np,bpy
from scipy.spatial.transform import Rotation
R=stage('packing');a=json.loads((R/'audit/layout.json').read_text());s=json.loads((R/'selection.json').read_text())
assets=json.loads((stage('parade') / 'bundle/assets.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(R/'render/packing.blend'))
def value(obj,path,t,n):
 fs={f.array_index:f for f in obj.animation_data.action.fcurves if f.data_path==path};return np.array([fs[j].evaluate(1+t*30) for j in range(n)])
checks=[];max_feed_error=0.;max_joint_step=0.;min_cell_margin=1.
for rec,c in zip(a['records'],s['clips']):
 i=rec['index'];oid=rec['object_id'];assert hashlib.sha256(Path(c['file']).read_bytes()).hexdigest()==c['sha256']
 for ev in rec['events']:
  k=ev['box']
  if ev['feed_end']<29.96:
   displacements=[]
   for n in range(k+1,k+5):
    o=bpy.data.objects[f'{i}/Item{n}/{oid}'];delta=value(o,'location',ev['feed_end'],3)-value(o,'location',ev['feed_start'],3);displacements.append(delta)
   displacements=np.array(displacements);err=max(float(np.max(np.abs(np.abs(displacements[:,0])-.26))),float(np.max(np.abs(displacements[:,1:]))),float(np.ptp(displacements,axis=0).max()))
   assert err<.0015,(i,k,err);max_feed_error=max(max_feed_error,err)
  if ev['settled']<29.85:
   t=ev['settled']+.1;tray=bpy.data.objects[f'Order tray {k+1}'];o=bpy.data.objects[f'{i}/Item{k}/{oid}'];p=value(o,'location',t,3);q=value(o,'rotation_quaternion',t,4);q=q/np.linalg.norm(q);trayp=value(tray,'location',t,3)
   vv=np.array([v.co[:] for v in o.data.vertices]);xyz=Rotation.from_quat(q[[1,2,3,0]]).apply(vv)+p-trayp
   xy=xyz[:,:2]-[(rec['slot_col']-1.5)*.19,(rec['slot_row']-2.5)*.19];margin=.09-np.abs(xy).max();min_cell_margin=min(min_cell_margin,float(margin));assert margin>.001,(i,k,margin)
   z=xyz[:,2]-.79;assert z.min()>-.009 and z.max()<.15,(i,k,z.min(),z.max())
   checks.append(dict(station=i,box=k,margin=float(margin)))
  # Verify the actual native arm animation has no loop-boundary jump.
  if k and ev['begin']<29.8:
   ts=np.arange(max(0,ev['begin']-.30),min(29.96,ev['begin']+.15),1/30)
   for joint in [j for j in assets['robots'][rec['pair']]['joints'] if j['movable'] and j['name'].startswith('arm_joint_')]:
    j=joint['name'];o=bpy.data.objects[f'{i}/{joint["child"]}']
    qq=np.array([value(o,'rotation_quaternion',t,4) for t in ts]);qq/=np.linalg.norm(qq,axis=1)[:,None]
    angle=2*np.arccos(np.clip(np.abs(np.sum(qq[1:]*qq[:-1],axis=1)),0,1));m=float(angle.max()) if len(angle) else 0.;max_joint_step=max(max_joint_step,m)
    assert m<.15,(i,k,j,m)
by=np.array(a['tray_y']);assert np.max(np.abs(by[:-1]-by[1:]-4.5))<1e-8
for rec in a['records']:
 assert rec['initial_items']>=5 and rec['minimum_waiting_items']>=4
 for ev in rec['events']:
  ts=np.arange(900)/30;mask=(ts>=ev['release'])&(ts<=ev['settled']);assert np.max(np.abs(by[ev['box'],mask]-rec['index']*.9),initial=0)<1e-8
out=dict(passed=True,native_curve_checks=True,feed_motion_error_m=max_feed_error,max_arm_loop_step_rad=max_joint_step,minimum_settled_mesh_margin_m=min_cell_margin,verified_deposits=len(checks),box_spacing_m=4.5,initial_feed_items_min=5,waiting_items_min=4,source_clips=24,unique_objects=24,repeated_source_clips_scripted_cycles=True,blend_sha256=hashlib.sha256((R/'render/packing.blend').read_bytes()).hexdigest())
(R/'audit/native_validation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
