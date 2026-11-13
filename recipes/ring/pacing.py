from dexvideo.paths import stage
"""Shared time reparameterization for recorded robot AND all objects; not new physics."""
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import PchipInterpolator

def pacing(d):
 q=d['q'];state=d['state'];dq=np.gradient(q,axis=0)*60
 active=np.ptp(q[:,7:],axis=0)>.1
 hand=np.sqrt(np.mean(dq[:,7:][:,active]**2,axis=1))
 arm=np.sqrt(np.mean(dq[:,:7]**2,axis=1))
 grasp=state==1
 ref=max(.2,float(np.percentile(hand[grasp],85)))
 burst=np.clip((gaussian_filter1d(hand,2)/ref-.35)/.5,0,1)
 rate=np.full(len(q),1.5)
 rate[grasp]=(1.45-.75*burst)[grasp]
 # Avoid accelerating an already fast arm segment.
 rate[grasp]=np.minimum(rate[grasp],np.clip(1.0/(arm[grasp]+.05),.7,1.45))
 transfer=state==2
 rate[transfer]=np.clip(.85/(gaussian_filter1d(arm,4)[transfer]+.05),1.6,2.3)
 rate[state==3]=1.25
 rate[state==4]=1.9
 rate=gaussian_filter1d(rate,8,mode='nearest')
 rate=np.clip(rate,.7,2.3)
 start=35;source=np.arange(start,len(q),dtype=float)
 elapsed=np.r_[0,np.cumsum((1/60)*2/(rate[start:-1]+rate[start+1:]))]
 inverse=PchipInterpolator(elapsed,source)
 return dict(rate=rate,elapsed=elapsed,source=source,inverse=inverse,hand=hand,arm=arm)

def sample(clock,times):
 return clock['inverse'](np.clip(times,0,clock['elapsed'][-1]))
