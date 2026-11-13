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

