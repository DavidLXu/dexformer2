from dexvideo.paths import stage
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
from native_helpers import *
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Slerp
V=stage('packing');END=900;FPS=30;fr=np.arange(1,END+1);times=(fr-1)/FPS
selection=json.loads((V/'selection.json').read_text());clips=selection['clips'];assert len(clips)==24 and selection['passed']
white=get_material(dict(type='principled',base_color={'type':'rgb','value':[.80,.84,.85]},roughness=.52))
metal=get_material(dict(type='principled',base_color={'type':'rgb','value':[.42,.47,.50]},metallic=.45,roughness=.38))
beltmat=get_material(dict(type='principled',base_color={'type':'rgb','value':[.11,.14,.15]},roughness=.72))
blue=get_material(dict(type='principled',base_color={'type':'rgb','value':[.045,.47,.57]},roughness=.40))
inside=get_material(dict(type='principled',base_color={'type':'rgb','value':[.26,.62,.67]},roughness=.55))
def box(name,loc,size,mat,parent=None,bevel=.006):
 mesh=bpy.data.meshes.new(name);x,y,z=np.array(size)/2
 mesh.from_pydata([(a*x,b*y,c*z) for a,b,c in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]],[],[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]);mesh.update()
 o=add_obj(name,mesh);o.location=loc;o.data.materials.append(mat)
 if parent:o.parent=parent
 if bevel:m=o.modifiers.new('Rounded edges','BEVEL');m.width=bevel;m.segments=2
 return o

def animpos(o,xyz):
 act=keyquat(o,np.tile([1,0,0,0],(END,1)),fr);animate_pos(o,np.asarray(xyz),fr,act)

def belt(name,center,length,width,along='y'):
 # All support surfaces are level and aligned, with no coplanar housing faces.
 sx,sy=(width,length) if along=='y' else (length,width)
 box(name+' housing',(*center,.695),(sx+.045,sy+.045,.10),white)
 box(name+' belt',(*center,.754),(sx,sy,.012),beltmat,bevel=.002)
 for s in [-1,1]:
  if along=='y':loc=(center[0]+s*(sx/2+.015),center[1],.758);sz=(.025,sy+.025,.025)
  else:loc=(center[0],center[1]+s*(sy/2+.015),.758);sz=(sx+.025,.025,.025)
  box(name+' rail',loc,sz,metal,bevel=.003)
 for dx in [-sx*.36,sx*.36]:
  for dy in [-sy*.40,sy*.40]:box(name+' leg',(center[0]+dx,center[1]+dy,.345),(.035,.035,.69),white)

# The entire main belt shares one stop-and-go displacement. Trays stay exactly five stations apart.
spacing=.90;gap_stations=5;gap=spacing*gap_stations;box_count=7
station_y=np.arange(24)*spacing;last=station_y[-1]
stop_indices=np.arange(60)
release_schedule=PchipInterpolator([0,1,2,3,7,15,23,29,59],[3.4,5.8,7.8,9.2,13.1,19.6,25.2,29.8,52.8])(stop_indices)
post_schedule=np.r_[.60,.55,.50,np.full(57,.34)]
anchors_t=[0.,.65];anchors_y=[-1.15,0.]
for step in range(60):
 anchors_t.extend([float(release_schedule[step]-.16),float(release_schedule[step]+post_schedule[step])]);anchors_y.extend([float(step*spacing)]*2)
assert np.all(np.diff(anchors_t)>0)
def smooth(u):
 u=np.clip(u,0,1);return u**3*(10-15*u+6*u*u)
def belt_y(t):
 k=np.clip(np.searchsorted(anchors_t,t,side='right')-1,0,len(anchors_t)-2)
 u=smooth((t-np.array(anchors_t)[k])/(np.array(anchors_t)[k+1]-np.array(anchors_t)[k]))
 return np.array(anchors_y)[k]+(np.array(anchors_y)[k+1]-np.array(anchors_y)[k])*u
by=belt_y(times);tray_positions=[by-k*gap for k in range(box_count)]
assert all(np.max(np.abs(tray_positions[k]-tray_positions[k+1]-gap))<1e-8 for k in range(box_count-1))
def visibility(obj,visible):
 changes=np.r_[0,np.flatnonzero(visible[1:]!=visible[:-1])+1]
 for j in changes:
  obj.hide_render=not bool(visible[j]);obj.keyframe_insert(data_path='hide_render',frame=int(j+1))
 if obj.animation_data:
  for curve in obj.animation_data.action.fcurves:
   if curve.data_path=='hide_render':
    for p in curve.keyframe_points:p.interpolation='CONSTANT'

def make_tray(parent):
 items=[]
 items.append(box('Tray floor',(0,0,.775),(.77,1.15,.03),inside,parent))
 for x in [-.385,.385]:items.append(box('Tray side',(x,0,.85),(.01,1.16,.12),blue,parent))
 for y in [-.575,.575]:items.append(box('Tray end',(0,y,.85),(.76,.01,.12),blue,parent))
 for x in [-.19,0,.19]:items.append(box('Tray divider',(x,0,.85),(.01,1.14,.12),inside,parent,bevel=.002))
 for y in [-.38,-.19,0,.19,.38]:items.append(box('Tray divider',(0,y,.85),(.76,.01,.12),inside,parent,bevel=.002))
 return items
for k in range(box_count):
 tray=add_obj(f'Order tray {k+1}');animpos(tray,np.c_[np.zeros(END),tray_positions[k],np.zeros(END)])
 for item in make_tray(tray):visibility(item,tray_positions[k]>-5.6)
main_min=-6.4;main_max=last+7.
belt('Main conveyor',(0,(main_min+main_max)/2),main_max-main_min,.83)
for y in np.arange(main_min+.3,main_max,1.8):
 for x in [-.36,.36]:box('Main support leg',(x,y,.345),(.045,.06,.69),white)
for y in np.arange(main_min,main_max,.11):
 o=box('Moving main rib',(0,y,.761),(.81,.008,.003),metal,bevel=0)
 ys=main_min+np.mod(y-main_min+by+1.15,main_max-main_min)
 animpos(o,np.c_[np.zeros(END),ys,np.full(END,.761)])
# Upstream cover hides incoming trays before they physically reach the belt.
box('Tray infeed cover',(0,-5.2,1.10),(.96,2.4,.055),white)
for x in [-.46,.46]:box('Tray infeed side',(x,-5.2,.91),(.04,2.4,.38),white)

records=[];feed_pitch=.26;feed_length=1.42
for i,c in enumerate(clips):
 pair=c['pair'];d=np.load(c['file']);assert hashlib.sha256(Path(c['file']).read_bytes()).hexdigest()==c['sha256']
 rr=Rotation.from_quat(d['root'][:,[4,5,6,3]]);pp=rr.inv().apply(d['pos']-d['root'][:,:3]);rq=(rr.inv()*Rotation.from_quat(d['quat'][:,[1,2,3,0]])).as_quat()
 cell_b=rr[0].inv().apply(d['bin_center']-d['root'][0,:3]);assert np.linalg.norm(cell_b-[.60,.22,.03])<1e-3
 col=[0,3,1,2][i%4];row=i//4;slot=np.array([(col-1.5)*.19,station_y[i]+(row-2.5)*.19,.79])
 side=-1 if col<2 else 1;yaw=-math.radians(55)+(0 if side<0 else math.pi);rot=Rotation.from_euler('z',yaw);base=slot-rot.apply(cell_b)
 assert abs(base[0])>.49
 start=35;rel=c['release'];sett=c['settled'];end=c['done'];lift=next(x['step'] for x in c['row']['events'] if x['to_state']==2)
 group=add_obj(f'{i:02d} {pair}');group.location=base;group.rotation_euler[2]=yaw;robot=assets['robots'][pair]
 q=np.tile(d['q'][start],(END,1));events=[];feed_progress=np.zeros(END);previous_end=None
 for k in range(box_count):
  step=i+gap_stations*k;release=float(release_schedule[step]);post=float(post_schedule[step]);endtime=release+post+.55
  pre=min(3.1,max(1.7,(rel-start)/60/1.30))
  begin=release-pre
  if i==0 and k==0:begin=.20
  if previous_end is not None:begin=max(begin,previous_end+.28)
  assert release-begin>1.3,(pair,k,release-begin)
  grasp_duration=min((release-begin)*.55,max(.75,min(1.4,(lift-start)/60)))
  tt=[begin,begin+grasp_duration,release,release+post,endtime];ss=[start,lift,rel,sett,end]
  srcmap=PchipInterpolator(tt,ss);source=np.clip(srcmap(np.clip(times,begin,endtime)),start,end)
  active=(times>=begin)&(times<=endtime)
  if previous_end is not None:
   blend=(times>previous_end)&(times<begin);u=smooth((times[blend]-previous_end)/(begin-previous_end))
   q[blend]=d['q'][end]*(1-u[:,None])+d['q'][start]*u[:,None]
  qa=np.column_stack([np.interp(source,np.arange(len(d['q'])),d['q'][:,j]) for j in range(29)])
  q[active]=qa[active];q[times>endtime]=d['q'][end]
  grid=np.linspace(begin,release,600);lift_t=float(np.interp(lift,srcmap(grid),grid))
  feed_start=lift_t+.20;feed_end=feed_start+.60
  assert feed_end<endtime
  if events:assert events[-1]['feed_end']<begin-.1,(pair,k)
  feed_progress+=smooth((times-feed_start)/.60)
  events.append(dict(box=k,step=step,begin=begin,grasp_duration=grasp_duration,release=release,settled=release+post,end=endtime,feed_start=feed_start,feed_end=feed_end,source=source))
  previous_end=endtime
 links={}
 for name in robot['roots']:o=add_obj(f'{i}/{name}');o.parent=group;links[name]=o
 for j in robot['joints']:
  o=add_obj(f'{i}/{j["child"]}');o.parent=links[j['parent']];origin=np.array(j['origin']);o.matrix_basis=Matrix(origin.tolist());links[j['child']]=o
  if j['movable']:
   jid=int(j['name'].rsplit('_',1)[1])-1 if j['name'].startswith('arm_joint_') else 7+int(j['name'].split('_')[1])
   quat=(Rotation.from_matrix(origin[:3,:3])*Rotation.from_rotvec(q[:,jid,None]*np.asarray(j['axis']))).as_quat()[:,[3,0,1,2]];keyquat(o,quat,fr)
 for part in robot['parts']:o=add_obj(f'{i}/CAD/{part["link"]}',get_mesh(part));o.parent=links[part['link']]
 pickup=rot.apply(pp[start])+base;inner=max(.46,abs(pickup[0])-.13);outer=inner+feed_length
 center=np.array([side*(inner+feed_length/2),pickup[1]])
 belt(f'{i} Extended feed',center,feed_length,.34,'x')
 # Shared belt motion for ALL waiting objects and ribs. No stationary decorative items.
 advance=feed_pitch*feed_progress
 for xoffset in np.arange(0,feed_length,.09):
  o=box('Moving side rib',(0,center[1],.761),(.007,.32,.003),metal,bevel=0)
  xr=inner+np.mod(xoffset-advance,feed_length)
  animpos(o,np.c_[side*xr,np.full(END,center[1]),np.full(END,.761)])
 # An opaque supply cover masks replenishment entering from upstream.
 box('Supply cover',(side*(outer+.14),center[1],.965),(.44,.39,.04),white)
 for y in [center[1]-.18,center[1]+.18]:box('Supply side',(side*(outer+.14),y,.85),(.44,.025,.23),white)
 box('Supply back',(side*(outer+.35),center[1],.85),(.025,.39,.23),white)
 queued_count=np.zeros(END,dtype=int);target_initial=0
 for k in range(box_count+5):
  worldp=np.tile(pickup,(END,1));worldp[:,0]+=side*feed_pitch*(k-feed_progress)
  worldr=np.tile((rot*Rotation.from_quat(rq[start])).as_quat()[[3,0,1,2]],(END,1))
  waiting=np.ones(END,dtype=bool)
  if k<box_count:
   ev=events[k];source=ev['source'];active=times>=ev['begin'];deposited=times>=ev['settled'];waiting=~active
   p=np.column_stack([np.interp(source,np.arange(len(pp)),pp[:,j]) for j in range(3)])
   quat=Slerp(np.arange(len(rq)),Rotation.from_quat(rq))(source)
   w=rot.apply(p)+base;wq=(rot*quat).as_quat()[:,[3,0,1,2]]
   w[deposited]=rot.apply(pp[sett])+base;w[deposited,1]+=tray_positions[k][deposited]-station_y[i]
   wq[deposited]=(rot*Rotation.from_quat(rq[sett])).as_quat()[[3,0,1,2]]
   worldp[active]=w[active];worldr[active]=wq[active]
  visible=(np.abs(worldp[:,0])<outer+.26)|(~waiting)
  queued_count+=((np.abs(worldp[:,0])>=inner+.05)&(np.abs(worldp[:,0])<=outer-.12)&waiting).astype(int)
  if abs(worldp[0,0])<outer-.12:target_initial+=1
  obj=add_obj(f'{i}/Item{k}/{c["object_id"]}',get_mesh(assets['objects'][c['object_id']]))
  action=keyquat(obj,worldr,fr);animate_pos(obj,worldp,fr,action);visibility(obj,visible)
 assert target_initial>=5,(pair,target_initial)
 # While a target is actively grasped there must still be four visible queued objects.
 assert queued_count.min()>=4,(pair,int(queued_count.min()))
 box('Robot pedestal',(base[0],base[1],.35),(.21,.23,.70),white)
 box('Robot mounting plate',(base[0],base[1],.735),(.26,.26,.05),metal)
 vv=np.load(B/assets['objects'][c['object_id']]['mesh'])['vertices'];wv=rot.apply(Rotation.from_quat(rq[start]).apply(vv)+pp[start])+base
 margin=min(feed_length/2-np.max(np.abs(wv[:,0]-center[0])),.17-np.max(np.abs(wv[:,1]-center[1])))
 assert margin>.030,(pair,margin)
 records.append(dict(index=i,pair=pair,object_id=c['object_id'],slot_col=col,slot_row=row,source_file=c['file'],source_sha256=c['sha256'],source_start=start,source_release=rel,source_settled=sett,source_end=end,base=base.tolist(),yaw=yaw,pickup_margin=float(margin),feed_length=feed_length,feed_pitch=feed_pitch,initial_items=target_initial,minimum_waiting_items=int(queued_count.min()),feed_progress=feed_progress.tolist(),feed_center=center.tolist(),events=[{k:v for k,v in e.items() if k!='source'} for e in events]))
 print('STATION',i,pair,'cycles',sum(e['begin']<30 for e in events),flush=True)

# Slower lead-tray following, then reveal multiple orders being packed concurrently.
cam=add_obj('Camera',bpy.data.cameras.new('Camera'));scene.camera=cam;cam.data.lens=36;cam.data.clip_end=180
ct=[0,3.3,5.8,7.8,13.1,19.6,25.5,28.5,30.]
cy=PchipInterpolator(ct,[-2.7,-2.7,-1.8,-.9,3.8,10.6,last-2.8,10.65,10.65])
cx=PchipInterpolator(ct,[1.25,1.25,1.25,1.3,1.7,2.5,3.3,26.,26.])
cz=PchipInterpolator(ct,[2.65,2.65,2.7,2.8,3.1,3.8,4.3,24.,24.])
look_y=PchipInterpolator(np.r_[0,release_schedule[:30],31.],np.r_[0,station_y,24*.9,25*.9,26*.9,27*.9,28*.9,29*.9,30*.9])
poses=[];qs=[]
for t in times:
 eye=Vector((float(cx(t)),float(cy(t)),float(cz(t))));target=Vector((-.20,float(look_y(t))-.20,.90))
 if t>25.5:
  u=float(smooth((t-25.5)/3.));target.y=target.y*(1-u)+10.65*u
 poses.append(eye[:]);qs.append((target-eye).to_track_quat('-Z','Y')[:])
a=keyquat(cam,qs,fr);animate_pos(cam,np.array(poses),fr,a)
floor=box('White floor',(0,last/2,-.06),(140,150,.1),white)
for k,y in enumerate(np.arange(-4,last+8,3.8)):
 light=bpy.data.lights.new(f'Softbox{k}','AREA');light.energy=650;light.shape='DISK';light.size=4
 o=add_obj(light.name,light);o.location=(-2 if k%2 else 2,y,5);o.rotation_euler=(Vector((0,y,.8))-o.location).to_track_quat('-Z','Y').to_euler()
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(1,1,1,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
scene.view_settings.exposure=-.45;scene.frame_end=END;scene.cycles.samples=24;scene.render.motion_blur_shutter=.16;scene.render.film_transparent=True;scene.render.image_settings.color_mode='RGBA'
(V/'render').mkdir(exist_ok=True);(V/'audit').mkdir(exist_ok=True);scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(V/'render/packing.blend'))
(V/'audit/layout.json').write_text(json.dumps(dict(passed=True,stations=24,unique_objects=24,fps=30,frames=900,seconds=30,records=records,lead_y=by.tolist(),tray_y=[x.tolist() for x in tray_positions],box_count=box_count,box_gap_stations=5,box_gap_m=gap,camera=poses,release_schedule=release_schedule.tolist(),scripted_transport_and_replenishment=True,repeated_success_clips=True,variable_speed_presentation=True),indent=2))
