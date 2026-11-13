from dexvideo.paths import stage
from pathlib import Path
import sys,json,hashlib
import numpy as np
from pacing import pacing,sample
R=stage('ring');S=R
selection=json.load(open(R/'selection.json'));layout=json.load(open(R/'audit/layout.json'));rows=[]
for i,c in enumerate(selection['clips']):
 p=Path(c['file']);assert hashlib.sha256(p.read_bytes()).hexdigest()==c['sha256'];d=np.load(p);clock=pacing(d)
 m=json.load(open(R/'audit'/f'time_map_{i:02d}.json'));src=np.array(m['source_frames']);rec=layout['stations_detail'][i]
 expected=sample(clock,np.maximum(0,np.arange(1,451)-rec['animation_start_frame'])/30)
 assert np.allclose(src,expected) and np.all(np.diff(src)>=0)
 assert np.all(src[:rec['animation_start_frame']]==35) and d['cycle'][35]==0
 assert c['row']['arrival_steps']==c['row']['release_steps'] and len(c['row']['release_steps'])==4
 g=d['state']==1;t=d['state']==2
 grasp_rate=float(np.median(clock['rate'][g]));transfer_rate=float(np.median(clock['rate'][t]))
 assert grasp_rate<1.5 and transfer_rate>1.5
 old95=float(np.percentile(clock['hand'][g]*1.5,95));new95=float(np.percentile((clock['hand']*clock['rate'])[g],95))
 assert new95<old95
 releases=[float(clock['elapsed'][n-35]) for n in c['row']['release_steps']]
 rows.append(dict(pair=c['pair'],sha_verified=True,median_grasp_playback=grasp_rate,median_transfer_playback=transfer_rate,grasp_hand_speed_p95_before=old95,grasp_hand_speed_p95_after=new95,release_times_after_start_seconds=releases))
hero_clock=pacing(np.load(S/'clips/franka_revo3.npz'));hero_open=hero_clock['elapsed'][selection['clips'][0]['row']['release_steps'][1]+18-35]
assert (layout['camera_departure_frame']-1)/30>hero_open
(R/'audit/pacing_validation.json').write_text(json.dumps(dict(passed=True,common_clock_for_all_moving_parts=True,source_paths_preserved=True,physics_rerun=False,variable_speed_presentation=True,hero_second_open_seconds=float(hero_open),camera_departure_seconds=(layout['camera_departure_frame']-1)/30,rows=rows),indent=2))
for row in rows[:4]:print(row)
