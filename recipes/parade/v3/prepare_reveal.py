from dexvideo.paths import stage
from pathlib import Path
import bpy,json,hashlib,shutil
R=(stage('parade') / '');V=R/'v3';(V/'render').mkdir(parents=True,exist_ok=True)
records=[]
for name,ids in [('hero',{0}),('local',{0,1,2,3})]:
 bpy.ops.wm.open_mainfile(filepath=str(R/'v2/render/parade.blend'))
 hidden=visible=0
 for o in bpy.data.objects:
  if o.type!='MESH' or not o.name[:3].isdigit():continue
  idx=int(o.name[:3]);o.hide_render=idx not in ids
  hidden+=int(o.hide_render);visible+=int(not o.hide_render)
 assert hidden>0 and visible>0
 bpy.ops.wm.save_as_mainfile(filepath=str(V/'render'/f'{name}.blend'))
 records.append(dict(stage=name,visible_robot_indices=sorted(ids),hidden_meshes=hidden,visible_meshes=visible))
shutil.copy2(R/'title.png',V/'title.png')
(V/'revision.json').write_text(json.dumps(dict(purpose='Editorial reveal: isolate first real grasp, reveal four-robot local view during camera transition, reveal full formation during axial pullback',stages=records,hero_only=[1,76],first_reveal=[77,105],local_only=[106,195],formation_reveal=[196,240],full_scene=[241,360],original_scene_sha256=hashlib.sha256((R/'v2/render/parade.blend').read_bytes()).hexdigest(),camera_and_physical_animation_unchanged=True),indent=2))
print('REVEAL_SCENES_READY',records,flush=True)
