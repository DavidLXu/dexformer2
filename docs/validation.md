# Release validation — 2026-11-14

The initial release was tested from the independent repository with a fresh Python3.11 environment and bpy4.5.3. External native assets were imported locally and are not part of the public Git tree.

- All six CLI entry points built native scenes: conveyor, Newton, ring, long-table, order-packing and apple index0.
- Each entry point rendered a native CPU preview from its newly built scene; the six-image contact sheet was visually reviewed.
- 204 selected trajectory files matched their recorded SHA-256 values; tests checked numeric joint/object arrays and source coverage.
- The680 imported mesh/texture files matched the asset manifest; mesh topology, finite vertices and normal/UV dimensions were checked.
- Ring shared-clock pacing validation passed on12configurations.
- Packing native audit passed: box gap4.5m/five stations, at least4queued objects per station,94replayed deposits, full-mesh cell containment and loop continuity. These94deposits are scripted repetitions of the selected recordings, not94new physical evaluation trials.
- The portable speed-overlay script encoded900frames/30seconds using the approved original packing film and the rebuilt timing audit.
- The generic encoder passed a90-frame/3-second fixture and complete decode. This fixture repeats a preview image solely to test encoding; it is not published as a robot demonstration.
- Five repository tests passed. They check source hashes, data shape/finiteness, native asset-index references, recipe parsing/portable paths, and the documented ring coverage.
- The publication tree was checked for credentials, private home/server paths and unintended large binaries.

The complete full-resolution films were not re-rendered for this packaging release. The original films remain unchanged. Final pixel identity across Blender versions, operating systems and rendering devices is not promised. Full native rendering from a fresh public clone still needs the external asset bundle described in assets.md; no public combined-bundle or checkpoint download is claimed.
