# Caterpillar v3 asset review

Status: visual review candidate; user approval is pending. App/device integration remains gated on that approval.

## Reference comparison

The approved caterpillar drawing and 3D reference were inspected alongside assets-src/v2/insects/caterpillar-beauty.png. The rebuilt body is one continuous weighted skin surface with broad connected folds, fine secondary wrinkles, a rounded tail, eight colored body bands and a cream head. The final pass replaced angular peg-like feet with rounded fleshy prolegs and flattened pads, and added rounded joints/pads to the slender anterior legs. Iterations corrected weak folds, washed-out pigment, excessive apparent surface fuzz, cropped natural framing, foot contact, and the pointed tail.

References: docs/visual-redesign/2026-10-08/01-insect-sheets-v1.png and 09-caterpillar-3d-v1.png in the same folder. All mesh geometry and pigment/PBR maps are authored assets. The renders use actual Blender geometry and materials; no generated concept image is used as a texture or background.

## Files and visual evidence

- caterpillar.blend: editable mesh, armature, five actions, packed images, separate review staging.
- caterpillar.glb: portable glTF 2.0 mesh, one skin, five animations and six embedded PBR images.
- 01-neutral-three-quarter.png: actual source asset under neutral lighting.
- 02-shape-check.png: orthographic silhouette view.
- 03-natural-leaf-closeup.png: actual full-subject leaf scene, with geometry and procedural distant foliage.
- 04-glb-roundtrip.png: corrected rest-pose roundtrip image; a copy of the independent fresh-process render below.
- 05-exported-animation-contact-sheet.png: three actual imported-GLB samples of each of the five actions.
- 06-fresh-process-roundtrip.png: fresh factory-startup process with only the GLB imported before QA staging.
- statistics.json, glb-structure-verification.json, fresh-process-verification.json and roundtrip-pixel-comparison.json: measured evidence.
- uv-linkage.json: drawing-region/UV mapping and the remaining painting integration steps.

## Measured asset budget

- 117,128 triangles; 61,467 source vertices; 92 exported mesh objects/primitives.
- 15 bones in one armature/skin; five exported and independently reimported actions.
- GLB size: 12,510,404 bytes (11.93 MiB).
- Rest bounding dimensions: 0.3239 x 0.0796 x 0.1234 metres, Blender XYZ. This is the authored display scale and can be uniformly scaled by the application.
- Six packed image maps, with no external image URI: 2048 x 1024 skin base color, normal and roughness; 512 x 512 cuticle base color, normal and roughness.
- Asset materials use portable base-color, normal and roughness inputs. The insect materials do not rely on procedural Blender shaders or preview-only subsurface scattering. Review leaves, floor, lighting and background are excluded from the GLB.

## Exported actions

- caterpillar_crawl: 3 seconds, 45 exported transform channels.
- caterpillar_explore: 4 seconds, 45 exported transform channels.
- caterpillar_idle_breathe: 4 seconds, 45 exported transform channels.
- caterpillar_recoil: 2 seconds, 45 exported transform channels.
- caterpillar_touch_curiosity: 3 seconds, 45 exported transform channels.

## Drawing linkage

The body uses one continuous 2048 x 1024 cylindrical atlas. UV u runs from tail to head; v runs around the skin. The tail uses u 0-0.06, the eight body regions divide u 0.06-0.90 into 0.105-wide intervals, and the head uses u 0.90-1.00. These correspond to the ten v3 line-art region labels and are listed in uv-linkage.json. Exact per-pixel transfer from the irregular 2D region shapes into curved skin remains implementation work. The current GLB carries static example pigment, not a working player-painting feature.

## Verification and practical limits

Fresh-process validation passed: mesh UVs, vertex groups, bone count, five actions and six packed images are present. The fresh rendered comparison against the neutral source has mean absolute RGB-byte error 0.338/255 and a 99th percentile error of 1.0/255. The actual pixels were inspected.

Blender's importer creates a hidden Icosphere bone-display helper and automatically activates the alphabetically first animation. QA disables that helper and clears animation pose bases before rendering the neutral rest pose; the animation sheet deliberately evaluates the named actions. This avoids mistaking the first crawl frame for the caterpillar's rest stance.

The caterpillar follows the illustrated proportions and color sequence. Its fine wrinkles and sparse setae remain stylized. The five clips use smooth bone weights and small peristaltic/exploration motions; they are authored in place and do not provide a runtime ground-contact or interaction system.

The files are supplied at review fidelity. LODs, texture compression, draw-call reduction and device performance measurements remain after visual approval. The natural scene is a review environment and is not included in the standalone insect export. Static sample colors, authored animations and successful GLB reimport do not imply that player painting or app interactions are already connected.
