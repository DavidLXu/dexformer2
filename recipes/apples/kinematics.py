from dexvideo.paths import stage
import numpy as np
from scipy.spatial.transform import Rotation

def fk(q,robot):
 n=len(q);T={name:np.broadcast_to(np.eye(4),(n,4,4)).copy() for name in robot['roots']}
 for j in robot['joints']:
  local=np.broadcast_to(np.asarray(j['origin']),(n,4,4)).copy()
  if j['movable']:
   jid=int(j['name'].rsplit('_',1)[1])-1 if j['name'].startswith('arm_joint_') else 7+int(j['name'].split('_')[1])
   rot=np.broadcast_to(np.eye(4),(n,4,4)).copy();rot[:,:3,:3]=Rotation.from_rotvec(q[:,jid,None]*np.asarray(j['axis'])).as_matrix();local=local@rot
  T[j['child']]=T[j['parent']]@local
 return T
