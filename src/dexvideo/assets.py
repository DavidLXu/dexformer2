"""Local asset import and pinned downloads; never re-license third-party data."""
from pathlib import Path
import hashlib,json,shutil,urllib.request
from .paths import REPO,stage

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def copy_verified(src,dst,digest=None):
    if digest and sha(src)!=digest:raise ValueError(f'Checksum mismatch: {src}')
    dst.parent.mkdir(parents=True,exist_ok=True)
    if not dst.exists():shutil.copy2(src,dst)
    elif sha(dst)!=sha(src):raise ValueError(f'Refusing to overwrite different data: {dst}')

def initialize():
    # Materialize portable selection manifests into a configurable work directory.
    for p in (REPO/'manifests/stages').rglob('*.json'):
        rel=p.relative_to(REPO/'manifests/stages');target=stage(str(rel.parent))/rel.name
        data=json.loads(p.read_text())
        def resolve(x):
            if isinstance(x,dict):return {k:resolve(v) for k,v in x.items()}
            if isinstance(x,list):return [resolve(v) for v in x]
            if isinstance(x,str) and x.startswith('$CLIPS/'):
                return str(stage(str(rel.parent))/'clips'/x.split('/',1)[1])
            return x
        target.write_text(json.dumps(resolve(data),indent=2))
    for root in (REPO/'trajectories').iterdir():
        if not root.is_dir():continue
        target=stage('parade/bundle' if root.name=='parade' else root.name)/'clips'
        for p in root.glob('*.npz'):copy_verified(p,target/p.name)
    for name in ['parade','parade/v3']:
        copy_verified(REPO/'branding/title.png',stage(name)/'title.png')

def import_bundle(source):
    source=Path(source).expanduser().resolve();index=json.loads((REPO/'manifests/render_bundle.json').read_text())
    for entry in index['files']:
        copy_verified(source/entry['path'],stage('parade/bundle')/entry['path'],entry['sha256'])
    print(f"Imported {len(index['files'])} verified mesh/texture files (local only).")

def import_tree(source=None):
    manifest=json.loads((REPO/'manifests/tree.json').read_text());dest=stage('parade/v4')/'assets'
    for item in manifest['files']:
        p=dest/item['file'];p.parent.mkdir(parents=True,exist_ok=True)
        if source:copy_verified(Path(source)/item['file'],p,item['sha256']);continue
        if p.exists() and sha(p)==item['sha256']:continue
        tmp=p.with_suffix(p.suffix+'.download')
        with urllib.request.urlopen(item['url'],timeout=60) as response,tmp.open('wb') as out:shutil.copyfileobj(response,out)
        if sha(tmp)!=item['sha256']:raise ValueError(f'Download hash mismatch: {item["file"]}')
        tmp.replace(p)

def missing_assets(tree=False):
    entries=json.loads((REPO/'manifests/render_bundle.json').read_text())['files']
    missing=[e['path'] for e in entries if not (stage('parade/bundle')/e['path']).exists()]
    if tree:
        for e in json.loads((REPO/'manifests/tree.json').read_text())['files']:
            if not (stage('parade/v4')/'assets'/e['file']).exists():missing.append('tree/'+e['file'])
    return missing
