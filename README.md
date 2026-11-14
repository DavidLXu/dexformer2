# DexFormer 2.0

[Project website](https://davidlxu.github.io/dexformer2-web/) · [Website source](https://github.com/DavidLXu/dexformer2-web)

> **Status.** This repository currently holds only the **video-rendering code** for the DexFormer 2.0 demonstration films, with the recorded trajectories they replay. Training code, the policy, evaluation scripts and model weights are **not here yet**; they will be added in a later update.

![Continuous order packing](docs/previews/order-packing.jpg)

## What you can do with it

| You want to… | Possible from a fresh clone? |
|---|---|
| Inspect the recorded joint and object trajectories | Yes |
| Read how each film is staged, timed and filmed | Yes |
| Run the tests and `dexvideo list` / `dexvideo doctor` | Yes |
| Build and render the films | **Only with a separate asset bundle** (robot and object meshes are not in this repository, and there is no public download yet) |
| Re-record new rollouts with the policy | No (needs the unreleased policy code, weights and simulator setup) |

If you only want to watch the films, they are on the [project website](https://davidlxu.github.io/dexformer2-web/).

## What the films are, and are not

The films **replay selected successful recordings** in staged scenes. They are illustrations, not evaluations:

- Each robot's motion comes from an independent recorded rollout; many robots in one shot were not simulated together.
- Camera motion, conveyor scheduling, reveals and repeated packing cycles are scripted.
- Depending on the recording, the transfer and release after a grasp use external inverse kinematics and scripted control.
- Nothing here measures a success rate.

Details per film: [docs/control-boundaries.md](docs/control-boundaries.md).

## Films

| Recipe | What it shows | Default output |
|---|---|---|
| `conveyor` | One station, then one row, then a 60-station production floor | 14.8 s, 30 fps |
| `newton` | Textured tree and falling apple, then the robot grasp reveal | 14.8 s, 30 fps |
| `ring` | Four objects per station, collected around a circle | 15 s, 60 fps |
| `long-table` | 24 robots along a table with a forward, descending camera | 15 s, 60 fps |
| `order-packing` | 24 configurations packing boxes from side feeders | 30 s, 30 fps |
| `apples` | One short clip per arm–hand combination grasping an apple at 0.5× speed | 24 clips, 30 fps |

`ring` uses 12 configurations (four arms, five hands); the RAPID hand is not in that selection. The other recipes use their own selections, listed in `manifests/stages/`.

Previews of every film: [docs/gallery.md](docs/gallery.md).

## Install

Requirements: Python **3.11** (other versions are rejected) and Blender's `bpy` **4.5.3**, which the `render` extra installs. All scenes are built and rendered with Blender (Cycles). Isaac Sim is not needed: it was used only to record the trajectories, which are already included.

```bash
git clone https://github.com/DavidLXu/dexformer2.git
cd dexformer2
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[render,dev]'
dexvideo list
```

Install in editable mode (`-e`) as shown: the recipes, manifests and trajectories are read from the checkout, not from the installed package. To run only the tests, `python -m pip install -e '.[dev]'` is enough and does not need Blender.

## Get the assets

Rendering needs two things that are not in Git.

**1. The native render bundle** (680 mesh and texture files for the robots and objects). There is **no public download yet**, because the robot models have different upstream licences. If you have a compatible bundle:

```bash
dexvideo import-assets /path/to/native-render-bundle   # every file is hash-checked
```

**2. The tree for the `newton` film** (CC0, from Poly Haven, about 130 MB):

```bash
dexvideo fetch-tree
```

Then check what is still missing:

```bash
dexvideo doctor
```

`doctor` exits with an error while assets are missing and also reports whether `bpy` is importable. The bundle layout, the upstream source of every model and the licence notes are in [docs/assets.md](docs/assets.md).

## Render a film

Each film goes through three steps: **build** the Blender scene, **render** the frames, **encode** the video.

```bash
dexvideo build  order-packing                      # assemble the scene and run its checks
dexvideo render order-packing --preview --frames 1,391,900   # quick quarter-size look at three frames
dexvideo render order-packing --device OPTIX       # all frames at full size
dexvideo encode order-packing                      # write work/packing/order-packing.mp4
```

Or all three at once:

```bash
dexvideo run ring --device OPTIX
```

The apple clips take an index from 0 to 23, one per arm–hand combination:

```bash
for i in $(seq 0 23); do dexvideo run apples --index "$i" --device OPTIX; done
```

To add the per-action playback-speed labels to the finished packing film (this reads the timing audit written by `dexvideo build order-packing`, so build the scene first):

```bash
dexvideo annotate-speed work/packing/order-packing.mp4
```

### Options

| Option | Applies to | Meaning |
|---|---|---|
| `--device CPU\|OPTIX\|CUDA\|METAL` | `render`, `run` | Render device. CPU is the default; OPTIX and CUDA need an NVIDIA GPU, METAL an Apple GPU. |
| `--preview` | `render`, `run` | Quarter resolution and at most 4 samples, written to a separate `preview/` folder. With `run`, no video is encoded. |
| `--frames 1,391,900` | `render`, `run` | Render only these output frames (1-based). Not available for the full `newton` render. |
| `--samples N` | `render`, `run` | Cycles samples per pixel (default 24). |
| `--batch N` | `render`, `run` | Frames rendered per Blender process (default 8). Blender is restarted between batches to keep memory bounded. |
| `--index 0..23` | all, for `apples` | Which arm–hand combination. |

### Where output goes

Everything is written under `work/` in the checkout, or under `$DEXVIDEO_WORK` if that variable is set. Each film has its own sub-folder with `render/` (the `.blend` scene), `frames/`, `preview/`, `audit/` and the final `.mp4`.

Rendered frames are reused on the next run only if the scene file, device, sample count, scale and frame rate are all unchanged; otherwise the renderer stops and asks for a different output folder. Use a new `DEXVIDEO_WORK` when you change settings.

### Things to know

- 60 fps films are sampled at true half-frame scene states; frames are not duplicated.
- `newton` is assembled from several separately rendered layers, so its full render always renders everything.
- Rendering uses four CPU threads per process. Start with one render at a time; long-running parallel jobs used too much memory in the original production.
- Output is not guaranteed to be pixel-identical across Blender versions, operating systems or devices.

## Repository layout

| Path | Contents |
|---|---|
| `src/dexvideo/` | Command-line tool: asset import, scene building, rendering, encoding |
| `recipes/` | Scene builders for each film, including the intermediate stages they depend on |
| `trajectories/` | Recorded joint and object tracks (`.npz`), unchanged from the originals |
| `manifests/` | Clip selections, asset hashes and sources, checkpoint identity, recipe lineage |
| `docs/` | Asset and licence notes, control boundaries, preview gallery, release validation |
| `tests/` | Checks on trajectory hashes and shapes, manifest coverage and path portability |

Run the tests with `python -m pytest -q`. What was and was not verified for this release is in [docs/validation.md](docs/validation.md).

## Model weights

Replaying the recorded trajectories needs no model. The recordings were made with the `morph16_healthy` policy at iteration 5,000 (SHA-256 `c68cb4c3…7c41e`, full value in `manifests/checkpoint.json`). The weights are not distributed here, and weights alone would not reproduce the rollouts without the matching policy code and simulation setup.

## License

Code written for this repository: [MIT](LICENSE). Numeric trajectory recordings: [CC BY 4.0](trajectories/LICENSE.txt). Third-party assets and trademarks keep their original terms; the code licence does not cover them.
