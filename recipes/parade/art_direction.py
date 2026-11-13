from dexvideo.paths import stage
"""Camera/light revision only. Physical robot and object playback is unchanged."""
from pathlib import Path
import json
import bpy
from mathutils import Vector
R=(stage('parade') / '')
def apply():
 s=bpy.context.scene;s.view_settings.exposure=.4;s.world.node_tree.nodes['Background'].inputs[1].default_value=.25
 for name,power in [('Key softbox',700),('Fill softbox',250),('Rear softbox',1100),('Soft daylight',1.0)]:bpy.data.lights[name].energy=power
 floor=bpy.data.objects['Continuous white studio surface'];floor.is_shadow_catcher=True;s.render.film_transparent=True
 s.use_nodes=False;s.render.image_settings.color_mode='RGBA'

 for o in bpy.data.objects:
  if o.name.startswith('Unit '):o.location.x*=1.4/1.7;o.location.y*=1.5/1.8
 cam=s.camera;data=cam.data;cam.animation_data_clear();data.animation_data_clear();data.dof.use_dof=True;data.dof.aperture_fstop=7.1
 keys=[(1,(.05,-2.55,1.20),(-.70,-.40,.43),43),(76,(-.30,-1.95,1.05),(-.70,-.45,.48),55),(91,(.6,-3.1,1.65),(0,-.25,.40),48),(148,(.7,-3.3,1.8),(0,-.2,.40),48),(171,(2.,-3.5,3.4),(0,.4,.40),50),(219,(1.9,-3.6,3.5),(0,.4,.40),50),(239,(-4.2,-1.8,1.6),(-3.5,2.,.5),35),(281,(4.6,-1.4,1.9),(3.3,2.7,.45),35),(300,(5.,-1.8,3.),(1.8,4.,.4),38),(363,(11.,-15.,15.),(0,4.8,.35),43),(420,(11.5,-15.7,15.8),(0,4.8,.35),43)]
 for frame,loc,target,lens in keys:
  cam.location=loc;cam.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler();cam.keyframe_insert('location',frame=frame);cam.keyframe_insert('rotation_euler',frame=frame);data.lens=lens;data.keyframe_insert('lens',frame=frame);data.dof.focus_distance=(Vector(target)-Vector(loc)).length;data.keyframe_insert('dof.focus_distance',frame=frame)
 for block in [cam,data]:
  for f in block.animation_data.action.fcurves:
   for k in f.keyframe_points:k.interpolation='BEZIER';k.handle_left_type='AUTO_CLAMPED';k.handle_right_type='AUTO_CLAMPED'
 s.frame_set(1)
 audit=json.loads((R/'render/trajectory_audit.json').read_text())
 for e in audit['entries']:
  o=bpy.data.objects[f'Unit {e["index"]:03d} {e["pair"]}'];e['group_translation']=list(o.location)
 audit['display_layout_revision']='1.4m columns,1.5m rows; white shadow catcher; close-to-wide camera'
 (R/'render/trajectory_audit.json').write_text(json.dumps(audit,indent=2))
if __name__=='__main__':
 bpy.ops.wm.open_mainfile(filepath=str(R/'render/parade.blend'));apply();bpy.ops.wm.save_as_mainfile(filepath=str(R/'render/parade.blend'))
