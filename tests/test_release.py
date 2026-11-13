from pathlib import Path
import hashlib,json,ast
import numpy as np
from dexvideo.paths import REPO

def test_selected_recordings_match_hash_and_shape():
    for p in (REPO/'manifests/stages').glob('*/selection.json'):
        data=json.loads(p.read_text());key=p.parent.name
        for c in data['clips']:
            file=REPO/'trajectories'/key/Path(c['file']).name
            assert hashlib.sha256(file.read_bytes()).hexdigest()==c['sha256']
            with np.load(file,allow_pickle=False) as arr:
                assert arr['q'].ndim==2 and arr['q'].shape[1]>=7
                assert np.isfinite(arr['q']).all()
                assert np.isfinite(arr['pos']).all()

def test_parade_recordings_match_hash():
    data=json.loads((REPO/'manifests/stages/parade/bundle/clips.json').read_text())
    for c in data['clips']:
        p=REPO/'trajectories/parade'/Path(c['file']).name
        assert hashlib.sha256(p.read_bytes()).hexdigest()==c['sha256']

def test_native_asset_index_covers_all_referenced_files():
    files={e['path'] for e in json.loads((REPO/'manifests/render_bundle.json').read_text())['files']}
    def walk(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if k in ['mesh','filename']:assert v in files
                walk(v)
        elif isinstance(x,list):
            for v in x:walk(v)
    walk(json.loads((REPO/'manifests/stages/parade/bundle/assets.json').read_text()))

def test_recipes_compile_and_have_no_fixed_home_paths():
    for p in list((REPO/'recipes').rglob('*.py'))+list((REPO/'src').rglob('*.py')):
        ast.parse(p.read_text())
        assert '/home/' not in p.read_text() and '/Users/' not in p.read_text()

def test_ring_truthful_coverage():
    d=json.loads((REPO/'manifests/stages/ring/selection.json').read_text());pairs={c['pair'] for c in d['clips']}
    assert len(pairs)==12
    assert len({p.split('_')[0] for p in pairs})==4
    assert len({p.split('_')[1] for p in pairs})==5
    assert not any(p.endswith('_rapid') for p in pairs)
