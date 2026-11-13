import argparse,json,sys
from .assets import initialize,import_bundle,import_tree,missing_assets
from .pipeline import SCENES,build,render,encode

def main():
    p=argparse.ArgumentParser(description='Native DexFormer video recipes. See README for external assets.');sp=p.add_subparsers(dest='command',required=True)
    sp.add_parser('list');sp.add_parser('doctor')
    a=sp.add_parser('annotate-speed');a.add_argument('video');a.add_argument('--output')
    a=sp.add_parser('import-assets');a.add_argument('bundle')
    a=sp.add_parser('fetch-tree');a.add_argument('--local-dir')
    for cmd in ['build','render','encode','run']:
        a=sp.add_parser(cmd);a.add_argument('scene',choices=SCENES);a.add_argument('--index',type=int,choices=range(24),default=0)
        if cmd in ['render','run']:
            a.add_argument('--preview',action='store_true');a.add_argument('--frames',help='Comma-separated output frame indices');a.add_argument('--device',choices=['CPU','OPTIX','CUDA','METAL'],default='CPU');a.add_argument('--samples',type=int,default=24);a.add_argument('--batch',type=int,default=8)
    a=p.parse_args()
    try:
        if a.command=='list':
            for n,c in SCENES.items():print(f'{n:16} {c["seconds"]:4g}s {c["fps"]}fps')
        elif a.command=='doctor':
            initialize();missing=missing_assets();print(json.dumps(dict(external_assets_missing=len(missing),first_missing=missing[:3],render_runtime=__import__('importlib.util').util.find_spec('bpy') is not None),indent=2));return 1 if missing else 0
        elif a.command=='annotate-speed':
            from .pipeline import run_recipe
            run_recipe('packing','add_speed.py',[a.video]+(['--output',a.output] if a.output else []))
        elif a.command=='import-assets':initialize();import_bundle(a.bundle)
        elif a.command=='fetch-tree':initialize();import_tree(a.local_dir)
        else:
            if a.command in ['build','run']:build(a.scene,a.index)
            if a.command in ['render','run']:
                if a.batch<1 or a.samples<1:raise ValueError('batch and samples must be positive')
                frames=[int(f) for f in a.frames.split(',')] if a.frames else None
                render(a.scene,a.index,a.preview,frames,a.device,a.samples,a.batch)
            if a.command=='encode' or (a.command=='run' and not a.preview and not a.frames):encode(a.scene,a.index)
    except (ValueError,RuntimeError,FileNotFoundError) as exc:p.exit(1,f'{exc}\n')
    return 0
if __name__=='__main__':sys.exit(main())
