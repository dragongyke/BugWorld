# Butterfly v3 asset review

Status: visual review candidate; user approval is pending. App/device integration remains gated on that approval.

## Reference comparison

The approved butterfly drawing and 3D reference were inspected alongside assets-src/v2/insects/butterfly-beauty.png. The rebuilt asset uses the same authored cubic wing outlines as the v3 line-art sheet, including the broad forewings, rounded hindwings, dark tips, scalloped margins, six lower-wing dots per side and branching veins. Pink-to-lavender wax strokes, shallow arched closed membranes, raised veins, 1,700 fine thoracic setae, a tapered annulated abdomen, clubbed antennae and six three-part articulated legs replace the flat and simplified v2 appearance. Iterations corrected excessive lighting, wing-view foreshortening, a mirrored flap direction and the leaf-review camera.

References: docs/visual-redesign/2026-10-08/01-insect-sheets-v1.png and 06-butterfly-3d-v1.png in the same folder. All mesh geometry and pigment/PBR maps are authored assets. The renders use actual Blender geometry and materials; no generated concept image is used as a texture or background.

## Files and visual evidence

- butterfly.blend: editable mesh, armature, five actions, packed images, separate review staging.
- butterfly.glb: portable glTF 2.0 mesh, one skin, five animations and six embedded PBR images.
- 01-neutral-three-quarter.png: actual source asset under neutral lighting.
- 02-shape-check.png: orthographic silhouette view.
- 03-natural-leaf-closeup.png: actual full-subject leaf scene, with geometry and procedural distant foliage.
- 04-glb-roundtrip.png: corrected rest-pose roundtrip image; a copy of the independent fresh-process render below.
- 05-exported-animation-contact-sheet.png: three actual imported-GLB samples of each of the five actions.
- 06-fresh-process-roundtrip.png: fresh factory-startup process with only the GLB imported before QA staging.
- statistics.json, glb-structure-verification.json, fresh-process-verification.json and roundtrip-pixel-comparison.json: measured evidence.
- uv-linkage.json: drawing-region/UV mapping and the remaining painting integration steps.

## Measured asset budget

- 55,688 triangles; 32,911 source vertices; 68 exported mesh objects/primitives.
- 25 bones in one armature/skin; five exported and independently reimported actions.
- GLB size: 20,142,340 bytes (19.21 MiB).
- Rest bounding dimensions: 0.2982 x 0.2202 x 0.1147 metres, Blender XYZ. This is the authored display scale and can be uniformly scaled by the application.
- Six packed image maps, with no external image URI: 2048 x 2048 wing base color, normal and roughness; 512 x 512 cuticle base color, normal and roughness.
- Asset materials use portable base-color, normal and roughness inputs. The insect materials do not rely on procedural Blender shaders or preview-only subsurface scattering. Review leaves, floor, lighting and background are excluded from the GLB.

## Exported actions

- butterfly_antenna_groom: 3 seconds, 75 exported transform channels.
- butterfly_fly: 1 seconds, 75 exported transform channels.
- butterfly_idle_perch: 4 seconds, 75 exported transform channels.
- butterfly_perch_touch: 2.67 seconds, 75 exported transform channels.
- butterfly_startle: 2 seconds, 75 exported transform channels.

## Drawing linkage

The four wing meshes share a 2048-square drawing atlas. The authored SVG source-crop coordinate maps to left-wing UV as u = 0.5 + (x - 251)/600 and v = 1 - (0.495 + (y - 190)/600); the right wing mirrors u. Region-to-mesh names and the sheet transform are recorded in uv-linkage.json. The sample base color currently contains both pigment and locked ink. A later painter integration must invert the sheet transform, composite player paint with the locked markings, and update the material texture. The current files demonstrate static sample artwork; player-driven painting has not been implemented.

## Verification and practical limits

Fresh-process validation passed: mesh UVs, vertex groups, bone count, five actions and six packed images are present. The fresh rendered comparison against the neutral source has mean absolute RGB-byte error 0.174/255 and a 99th percentile error of 1.0/255. The actual pixels were inspected.

Blender's importer creates a hidden Icosphere bone-display helper and automatically activates the alphabetically first animation. QA disables that helper and clears animation pose bases before rendering the neutral rest pose; the animation sheet deliberately evaluates the named actions. This avoids mistaking the first crawl frame for the caterpillar's rest stance.

The butterfly is a stylized interpretation of the approved art. Thoracic setae and small leg joints are most visible at close range. The five clips are authored in-place skeletal behaviors; flight translation, contact solving and interaction triggers belong to the later application integration.

The files are supplied at review fidelity. LODs, texture compression, draw-call reduction and device performance measurements remain after visual approval. The natural scene is a review environment and is not included in the standalone insect export. Static sample colors, authored animations and successful GLB reimport do not imply that player painting or app interactions are already connected.
