# Assets, trajectories and checkpoints

The public release separates replay data from trained policy weights and third-party geometry.

| Component | In Git? | Needed for |
|---|---:|---|
| Scene, camera, pacing, rendering and encoding scripts | Yes | Building films |
| Selected numeric joint/object trajectories | Yes | Replaying recorded actions |
| Mesh/material index and pinned file hashes | Yes | Identifying the exact native assets |
| Robot meshes, object textures and derived geometry | No | Full native rendering |
| Poly Haven tree | Download command | Newton prologue |
| Trained policy checkpoint | No | New policy inference/recording only |
| Isaac Sim / Isaac Lab policy environment | No | New physical rollouts |

## Exact native bundle

`dexvideo import-assets PATH` expects the already-exported **native render bundle**, not a URDF directory:

```text
PATH/
  meshes/<content-hash>.npz
  textures/<content-hash>.<png|jpg|...>
```

The `assets.json` index is supplied in `manifests/stages/parade/bundle/`. Robot entries contain `roots`, `joints` (origin transforms, axes, movable flags) and link-local mesh/material `parts`. Object entries contain mesh/material specifications. Mesh NPZ files contain `vertices`, triangular `faces`, `normals` and optional per-vertex `uv`. Textures use relative paths. The renderer preserves those authored kinematics and native visual geometries, including the camera/bracket-trimmed RAPID hand.

`manifests/render_bundle.json` lists 680 required mesh/texture files with SHA-256 checksums. Import checks every file. Original numeric motion tracks are distributed independently under `trajectories/`.

**The exact combined bundle does not currently have a public download endpoint.** A new public checkout can inspect and validate scripts/recordings but needs a separately obtained compatible bundle to render the full robots. Importing arbitrary upstream URDFs will not automatically reproduce the authored link alignment or materials. The index and upstream sources are an asset specification, not a promise of a one-command URDF conversion. This limitation is explicit until the combined asset release is cleared and hosted.

## Sources and notices

The recorded source snapshots and pinned commits are in `manifests/asset_sources.json`; object download provenance is in `manifests/object_sources.json`. These sources are not automatically cloned or uploaded.

- KUKA iiwa7: [LBR-Stack description](https://github.com/lbr-stack/lbr_iiwa7_r800_description), pinned source commit in the manifest.
- Flexiv: [manufacturer description](https://github.com/flexivrobotics/flexiv_description); source visual assets retain their own terms.
- Revo3: [RevoSim](https://github.com/BrainCoTech/RevoSim), MIT repository license and separate third-party notices are retained in `docs/licenses/`. Individual assets may carry additional notices.
- Sharpa: [official URDF/USD/XML](https://github.com/sharpa-robotics/sharpa-urdf-usd-xml); recorded Apache-2.0 license/notice snapshots are retained.
- Allegro: [Wonik Robotics](https://github.com/Wonikrobotics-git/allegro_hand_linux_v4).
- RAPID: [RAPID-Hand](https://github.com/SYSU-RoboticsLab/RAPID-Hand), recorded **CC BY-NC-SA 4.0** terms. The derived camera-free visual geometry is also excluded from Git.
- xArm7: [xArm description](https://github.com/xArm-Developer/xarm_ros/tree/master/xarm_description).
- YCB and the ManiTwin/RevoBench-derived object downloads: see object manifests. A local YCB license note is preserved; the release does not make a blanket redistribution grant for every object model.
- Franka, LEAP and Shadow visual components are identified by the bundle index; full per-file upstream redistribution review remains outstanding, so the combined pack is not published.

The Newton tree is [Poly Haven tree_small_02](https://polyhaven.com/a/tree_small_02), with [CC0 assets](https://polyhaven.com/license). `dexvideo fetch-tree` downloads the recorded URLs and verifies every hash in `manifests/tree.json`. The tree is artistically dressed with apples; it is not claimed to be a botanical apple-tree model.

Code licensing does not replace any of these asset licenses. The code release does not grant rights to manufacturer trademarks.

## Checkpoint

The recordings use `morph16_healthy`, iteration **5000**:

```text
SHA-256 c68cb4c3fbba4bee2f6cc7078ead267a90a76c7c27c71f7d6b81860042a7c41e
```

`manifests/checkpoint.json` intentionally has no public download URL. No weight file is bundled. Replay needs only the saved numeric trajectories. New inference requires the exact weights plus matching observation normalization, action definitions, embodiment configuration, policy implementation and simulation environment. These are not included in the current release; the full project code is planned for this repository. This repository does not claim that a weight file alone reproduces those rollouts.

If model weights or a fully cleared asset bundle are later released, host the versioned large files in a GitHub Release or model/dataset host and add their immutable URLs and hashes. Keep them out of ordinary Git history.
