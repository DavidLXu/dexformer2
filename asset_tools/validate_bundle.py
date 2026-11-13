"""Validate an imported native mesh bundle without Blender."""
from dexvideo.paths import REPO,stage
from dexvideo.assets import sha
import json,numpy as np
entries=json.loads((REPO/'manifests/render_bundle.json').read_text())['files']
for item in entries:
    p=stage('parade/bundle')/item['path']
    assert sha(p)==item['sha256'],p
    if p.suffix=='.npz':
        with np.load(p,allow_pickle=False) as d:
            v=d['vertices'];f=d['faces']
            assert v.ndim==2 and v.shape[1]==3 and np.isfinite(v).all()
            assert f.ndim==2 and f.shape[1]==3 and f.min()>=0 and f.max()<len(v)
            assert d['normals'].shape==v.shape
            if 'uv' in d:assert d['uv'].shape==(len(v),2)
print('Native asset bundle verified:',len(entries),'files')
